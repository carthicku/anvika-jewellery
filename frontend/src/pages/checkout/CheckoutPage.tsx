import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { Lock, ShoppingBag } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm, useWatch, type FieldPath, type UseFormReturn } from 'react-hook-form';
import { Link } from 'react-router';
import { z } from 'zod';

import { ApiError } from '@/api/client';
import { useAddresses, useMe, type Address } from '@/api/queries/account';
import { useCart } from '@/api/queries/cart';
import {
  useCheckoutQuote,
  usePlaceOrder,
  type CheckoutOrder,
  type CreateOrderInput,
} from '@/api/queries/orders';
import { queryKeys } from '@/api/queryKeys';
import { Container, PageHeader, PageMeta } from '@/components/layout/Page';
import { PriceSummary } from '@/components/orders/PriceSummary';
import { usePaymentFlow } from '@/components/orders/PaymentFlow';
import { ProductImage } from '@/components/product/ProductImage';
import { Button } from '@/components/ui/Button';
import { Alert, EmptyState, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { FormField, Input, Select, Textarea } from '@/components/ui/Field';
import { Spinner } from '@/components/ui/Spinner';
import { cn } from '@/lib/cn';
import { formatMoney, formatShortDate, hasPaise } from '@/lib/format';
import { errorMessage } from '@/lib/forms';
import { addressSchema, email, INDIAN_STATES } from '@/lib/validation/account';

const PINCODE_RE = /^[1-9][0-9]{5}$/;
const ADDRESS_KEYS = [
  'full_name',
  'phone',
  'line1',
  'line2',
  'landmark',
  'city',
  'state',
  'pincode',
] as const;

const addressFields = addressSchema.pick({
  full_name: true,
  phone: true,
  line1: true,
  line2: true,
  landmark: true,
  city: true,
  state: true,
  pincode: true,
});
type AddressValues = z.infer<typeof addressFields>;

const looseAddress = z.object(
  Object.fromEntries(ADDRESS_KEYS.map((k) => [k, z.string()])) as Record<
    (typeof ADDRESS_KEYS)[number],
    z.ZodString
  >,
);

function makeSchema(isGuest: boolean, usingSaved: boolean) {
  return z
    .object({
      email: z.string().trim(),
      shipping: looseAddress,
      billingSame: z.boolean(),
      billing: looseAddress,
      method: z.string().min(1, 'Choose a delivery option.'),
      note: z.string().trim().max(500, 'Please keep the note under 500 characters.'),
      terms: z.boolean().refine((v) => v, 'Please accept the terms to place your order.'),
    })
    .superRefine((values, ctx) => {
      if (isGuest && !email.safeParse(values.email).success) {
        ctx.addIssue({ code: 'custom', path: ['email'], message: 'Enter a valid email address.' });
      }
      const check = (prefix: 'shipping' | 'billing') => {
        const result = addressFields.safeParse(values[prefix]);
        if (!result.success) {
          for (const issue of result.error.issues) {
            ctx.addIssue({ code: 'custom', path: [prefix, ...issue.path], message: issue.message });
          }
        }
      };
      if (!usingSaved) check('shipping');
      if (!values.billingSame) check('billing');
    });
}
type CheckoutValues = z.infer<ReturnType<typeof makeSchema>>;

const EMPTY_ADDRESS = Object.fromEntries(ADDRESS_KEYS.map((k) => [k, ''])) as Record<
  (typeof ADDRESS_KEYS)[number],
  string
>;

function toAddressInput(values: Record<(typeof ADDRESS_KEYS)[number], string>) {
  const v = values as AddressValues;
  return { ...v, line2: v.line2 || null, landmark: v.landmark || null };
}

function fromSaved(address: Address): Record<(typeof ADDRESS_KEYS)[number], string> {
  return {
    full_name: address.full_name,
    phone: address.phone,
    line1: address.line1,
    line2: address.line2 ?? '',
    landmark: address.landmark ?? '',
    city: address.city,
    state: address.state,
    pincode: address.pincode,
  };
}

/** Backend field names → this form's field names, for server-side validation messages. */
function formField(serverField: string): FieldPath<CheckoutValues> | null {
  const [head, tail] = serverField.split('.', 2);
  if (head === 'shipping_address' && tail) return `shipping.${tail}` as FieldPath<CheckoutValues>;
  if (head === 'billing_address' && tail) return `billing.${tail}` as FieldPath<CheckoutValues>;
  if (head === 'email') return 'email';
  if (head === 'shipping_method') return 'method';
  if (head === 'terms_accepted') return 'terms';
  if (head === 'customer_note') return 'note';
  return null;
}

function AddressFields({
  form,
  prefix,
}: {
  form: UseFormReturn<CheckoutValues>;
  prefix: 'shipping' | 'billing';
}) {
  const errors = form.formState.errors[prefix];
  const auto = prefix === 'shipping' ? 'shipping' : 'billing';
  return (
    <div className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <FormField label="Full name" required error={errors?.full_name?.message}>
          <Input autoComplete={`${auto} name`} {...form.register(`${prefix}.full_name`)} />
        </FormField>
        <FormField label="Mobile number" required error={errors?.phone?.message}>
          <Input
            type="tel"
            inputMode="tel"
            autoComplete={`${auto} tel`}
            {...form.register(`${prefix}.phone`)}
          />
        </FormField>
      </div>
      <FormField label="House / flat, building, street" required error={errors?.line1?.message}>
        <Input autoComplete={`${auto} address-line1`} {...form.register(`${prefix}.line1`)} />
      </FormField>
      <div className="grid gap-5 sm:grid-cols-2">
        <FormField label="Area, locality" hint="Optional" error={errors?.line2?.message}>
          <Input autoComplete={`${auto} address-line2`} {...form.register(`${prefix}.line2`)} />
        </FormField>
        <FormField label="Landmark" hint="Optional" error={errors?.landmark?.message}>
          <Input {...form.register(`${prefix}.landmark`)} />
        </FormField>
      </div>
      <div className="grid gap-5 sm:grid-cols-3">
        <FormField label="PIN code" required error={errors?.pincode?.message}>
          <Input
            inputMode="numeric"
            autoComplete={`${auto} postal-code`}
            maxLength={6}
            {...form.register(`${prefix}.pincode`)}
          />
        </FormField>
        <FormField label="City" required error={errors?.city?.message}>
          <Input autoComplete={`${auto} address-level2`} {...form.register(`${prefix}.city`)} />
        </FormField>
        <FormField label="State / UT" required error={errors?.state?.message}>
          <Select autoComplete={`${auto} address-level1`} {...form.register(`${prefix}.state`)}>
            <option value="">Choose…</option>
            {INDIAN_STATES.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </Select>
        </FormField>
      </div>
    </div>
  );
}

function Step({
  number,
  title,
  children,
  aside,
}: {
  number: number;
  title: string;
  children: React.ReactNode;
  aside?: React.ReactNode;
}) {
  const id = `checkout-step-${String(number)}`;
  return (
    <section aria-labelledby={id} className="border-t border-line pt-8">
      <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={id} className="font-display text-2xl">
          <span className="mr-2 text-gold-deep">{number}.</span>
          {title}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

export function CheckoutPage() {
  const me = useMe();
  const user = me.data ?? null;
  const isGuest = !user;
  const cart = useCart();
  const addresses = useAddresses(!isGuest);
  const queryClient = useQueryClient();
  const place = usePlaceOrder();
  const [placed, setPlaced] = useState<CheckoutOrder | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const idempotency = useRef<{ payload: string; key: string } | null>(null);
  const flow = usePaymentFlow(
    placed?.order.reference ?? null,
    placed?.order.totals.grand_total ?? null,
  );

  // Signed-in customers start with their default delivery address.
  const saved = addresses.data ?? [];
  const preferred = saved.find((a) => a.is_default_shipping) ?? saved[0];
  const selectedId = isGuest ? 'new' : (savedId ?? preferred?.id ?? 'new');
  const selectedAddress = saved.find((a) => a.id === selectedId) ?? null;

  const schema = useMemo(
    () => makeSchema(isGuest, selectedAddress !== null),
    [isGuest, selectedAddress],
  );
  const form = useForm<CheckoutValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: '',
      shipping: { ...EMPTY_ADDRESS },
      billingSame: true,
      billing: { ...EMPTY_ADDRESS },
      method: '',
      note: '',
      terms: false,
    },
  });
  const { errors } = form.formState;

  const [typedPincode, method, billingSame] = useWatch({
    control: form.control,
    name: ['shipping.pincode', 'method', 'billingSame'],
  });
  const pincode = selectedAddress ? selectedAddress.pincode : typedPincode;
  const validPin = PINCODE_RE.test(pincode.trim()) ? pincode.trim() : null;
  const quote = useCheckoutQuote(validPin, method || null);
  const quoteData = validPin ? quote.data : undefined;

  // Keep the chosen delivery option valid for the current PIN code.
  useEffect(() => {
    if (!quoteData) return;
    const codes = quoteData.shipping_options.map((o) => o.code);
    if (quoteData.shipping_method && !codes.includes(method)) {
      form.setValue('method', quoteData.shipping_method);
    }
  }, [quoteData, method, form]);

  const view = quoteData?.cart ?? cart.data;
  const totals = quoteData?.cart.totals ?? null;
  const blocking = quoteData?.cart.blocking_issues ?? cart.data?.blocking_issues ?? [];
  const canPlace = Boolean(quoteData?.cart.can_checkout && totals && quoteData.serviceable);

  const onValid = (values: CheckoutValues) => {
    if (!totals) return;
    const body: CreateOrderInput = {
      email: isGuest ? values.email : null,
      shipping_address: toAddressInput(
        selectedAddress ? fromSaved(selectedAddress) : values.shipping,
      ),
      billing_address: values.billingSame ? null : toAddressInput(values.billing),
      shipping_method: values.method,
      expected_total: totals.grand_total,
      terms_accepted: values.terms,
      customer_note: values.note || null,
    };
    // Same details → same key, so a double click or a network retry never creates two orders.
    const payload = JSON.stringify(body);
    if (idempotency.current?.payload !== payload) {
      idempotency.current = { payload, key: crypto.randomUUID() };
    }
    place.mutate(
      { body, key: idempotency.current.key },
      {
        onSuccess: (result) => {
          setPlaced(result);
          if (result.payment) flow.start(result.payment, result.order.reference);
        },
        onError: (error) => {
          if (!(error instanceof ApiError)) return;
          for (const [field, message] of Object.entries(error.fieldErrors)) {
            const name = formField(field);
            if (name) form.setError(name, { message });
          }
          if (
            ['PRICE_CHANGED', 'CART_NOT_READY', 'OUT_OF_STOCK', 'CART_EMPTY'].includes(
              error.code,
            ) ||
            error.code.startsWith('COUPON_')
          ) {
            void queryClient.invalidateQueries({ queryKey: queryKeys.cart });
            void queryClient.invalidateQueries({ queryKey: ['checkout'] });
          }
        },
      },
    );
  };

  const onSubmit = (event: React.SyntheticEvent<HTMLFormElement>) => {
    void form.handleSubmit(onValid, () => {
      // Move focus to the first problem so keyboard and screen-reader users find it.
      requestAnimationFrame(() => {
        document.querySelector<HTMLElement>('form [aria-invalid="true"]')?.focus();
      });
    })(event);
  };

  if (cart.isPending || me.isPending) {
    return (
      <Container className="pb-24">
        <PageHeader title="Checkout" />
        <div className="grid gap-10 lg:grid-cols-[1fr_26rem]">
          <Skeleton className="h-96" />
          <Skeleton className="h-80" />
        </div>
      </Container>
    );
  }
  if (cart.isError) {
    return (
      <Container className="pb-24">
        <PageHeader title="Checkout" />
        <ErrorState error={cart.error} onRetry={() => void cart.refetch()} />
      </Container>
    );
  }
  if (cart.data.lines.length === 0 && !placed) {
    return (
      <Container className="pb-24">
        <PageMeta title="Checkout" path="/checkout" noindex />
        <PageHeader title="Checkout" />
        <EmptyState
          icon={ShoppingBag}
          title="Your cart is empty"
          action={
            <Button asChild>
              <Link to="/collections">Explore the collection</Link>
            </Button>
          }
        >
          Add a piece to your cart to check out.
        </EmptyState>
      </Container>
    );
  }

  const placeError = place.error instanceof ApiError ? place.error : null;
  const issues =
    placeError && Array.isArray(placeError.details.blocking_issues)
      ? (placeError.details.blocking_issues as string[])
      : [];
  const paise = view?.lines.some((l) => hasPaise(l.line_total)) ?? false;

  return (
    <>
      <PageMeta title="Checkout" path="/checkout" noindex />
      {flow.simulatedDialog}
      <Container className="pb-24">
        <PageHeader title="Checkout" />
        <form noValidate onSubmit={onSubmit}>
          <div className="grid gap-10 lg:grid-cols-[1fr_26rem] lg:items-start">
            <div className="min-w-0 space-y-10">
              <Step
                number={1}
                title="Contact"
                aside={
                  isGuest ? (
                    <Link
                      to="/login?next=/checkout"
                      className="text-sm underline underline-offset-4"
                    >
                      Have an account? Sign in
                    </Link>
                  ) : null
                }
              >
                {isGuest ? (
                  <FormField
                    label="Email"
                    required
                    hint="We'll send your order confirmation here."
                    error={errors.email?.message}
                  >
                    <Input type="email" autoComplete="email" {...form.register('email')} />
                  </FormField>
                ) : (
                  <p className="text-sm">
                    Signed in as <span className="font-medium">{user.email}</span>. Your order
                    confirmation will be sent to this address.
                  </p>
                )}
              </Step>

              <Step number={2} title="Delivery address">
                {!isGuest && saved.length > 0 && (
                  <fieldset className="mb-6 space-y-3">
                    <legend className="mb-2 text-sm font-medium">Saved addresses</legend>
                    {saved.map((address) => (
                      <label
                        key={address.id}
                        className={cn(
                          'flex cursor-pointer gap-3 rounded-md border p-4 text-sm',
                          selectedId === address.id ? 'border-ink' : 'border-line',
                        )}
                      >
                        <input
                          type="radio"
                          name="saved-address"
                          className="mt-1 size-4 accent-ink"
                          checked={selectedId === address.id}
                          onChange={() => {
                            setSavedId(address.id);
                          }}
                        />
                        <span className="sr-only">Deliver to </span>
                        <span>
                          <span className="font-medium">
                            {address.label ? `${address.label} · ` : ''}
                            {address.full_name}
                          </span>
                          <span className="block text-ink-muted">
                            {address.line1}
                            {address.line2 ? `, ${address.line2}` : ''}, {address.city},{' '}
                            {address.state} {address.pincode}
                          </span>
                        </span>
                      </label>
                    ))}
                    <label
                      className={cn(
                        'flex cursor-pointer gap-3 rounded-md border p-4 text-sm',
                        selectedId === 'new' ? 'border-ink' : 'border-line',
                      )}
                    >
                      <input
                        type="radio"
                        name="saved-address"
                        className="mt-1 size-4 accent-ink"
                        checked={selectedId === 'new'}
                        onChange={() => {
                          setSavedId('new');
                        }}
                      />
                      <span className="font-medium">Use a new address</span>
                    </label>
                  </fieldset>
                )}
                {!isGuest && addresses.isPending ? (
                  <Skeleton className="h-40" />
                ) : selectedAddress ? (
                  errors.shipping ? (
                    <Alert tone="danger">
                      This saved address needs updating before it can be used. Choose “Use a new
                      address” or edit it in your account.
                    </Alert>
                  ) : null
                ) : (
                  <AddressFields form={form} prefix="shipping" />
                )}
              </Step>

              <Step number={3} title="Delivery method">
                {!validPin ? (
                  <p className="text-sm text-ink-muted">
                    Enter a 6-digit PIN code above to see delivery options.
                  </p>
                ) : quote.isPending ? (
                  <p className="flex items-center gap-2 text-sm text-ink-muted" role="status">
                    <Spinner className="size-4" /> Checking delivery to {validPin}…
                  </p>
                ) : quote.isError ? (
                  <Alert tone="danger" title={errorMessage(quote.error)} />
                ) : quoteData && !quoteData.serviceable ? (
                  <Alert tone="warning">{quoteData.message}</Alert>
                ) : quoteData ? (
                  <fieldset className="space-y-3">
                    <legend className="sr-only">Delivery options for {validPin}</legend>
                    {quoteData.shipping_options.map((option) => (
                      <label
                        key={option.code}
                        className={cn(
                          'flex cursor-pointer items-start justify-between gap-4 rounded-md border p-4 text-sm',
                          method === option.code ? 'border-ink' : 'border-line',
                        )}
                      >
                        <span className="flex gap-3">
                          <input
                            type="radio"
                            value={option.code}
                            className="mt-1 size-4 accent-ink"
                            {...form.register('method')}
                          />
                          <span>
                            <span className="block font-medium">{option.name}</span>
                            <span className="block text-ink-muted">
                              Estimated {formatShortDate(option.estimated_from)} –{' '}
                              {formatShortDate(option.estimated_to)}
                            </span>
                          </span>
                        </span>
                        <span className="tabular shrink-0">
                          {method === option.code && totals
                            ? totals.shipping_fee === '0.00'
                              ? 'Free'
                              : formatMoney(totals.shipping_fee)
                            : formatMoney(option.fee)}
                        </span>
                      </label>
                    ))}
                    {errors.method && (
                      <p className="text-sm text-danger">{errors.method.message}</p>
                    )}
                  </fieldset>
                ) : null}
              </Step>

              <Step number={4} title="Billing address">
                <label className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="size-4 accent-ink"
                    {...form.register('billingSame')}
                  />
                  Same as delivery address
                </label>
                {!billingSame && (
                  <div className="mt-6">
                    <AddressFields form={form} prefix="billing" />
                  </div>
                )}
              </Step>

              <Step number={5} title="Order note">
                <FormField
                  label="Anything we should know?"
                  hint="Optional, e.g. gift wrapping or delivery instructions"
                  error={errors.note?.message}
                >
                  <Textarea rows={3} maxLength={500} {...form.register('note')} />
                </FormField>
              </Step>
            </div>

            <aside
              aria-labelledby="checkout-summary"
              className="rounded-md border border-line bg-surface p-6 lg:sticky lg:top-32"
            >
              <h2 id="checkout-summary" className="font-display text-2xl">
                Your order
              </h2>
              <ul className="mt-4 divide-y divide-line border-b border-line">
                {view?.lines.map((line) => (
                  <li key={line.id} className="flex gap-3 py-3 text-sm">
                    <div className="w-14 shrink-0 overflow-hidden rounded-sm bg-surface-muted">
                      {line.image && (
                        <ProductImage
                          image={line.image}
                          sizes="56px"
                          className="aspect-4/5 h-full w-full object-cover"
                        />
                      )}
                    </div>
                    <div className="flex min-w-0 flex-1 justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-medium">{line.product_name}</p>
                        <p className="text-ink-muted">
                          {line.variant_label} · Qty {line.quantity}
                        </p>
                      </div>
                      <p className="tabular shrink-0">
                        {line.line_total ? formatMoney(line.line_total, { paise }) : '—'}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>

              {totals ? (
                <PriceSummary
                  className="mt-4"
                  rows={totals.breakdown}
                  shippingLabel={totals.shipping_label}
                />
              ) : (
                <p className="mt-4 text-sm text-ink-muted">
                  Enter your delivery PIN code to see the final total with delivery.
                </p>
              )}

              {blocking.length > 0 && (
                <Alert tone="warning" title="Please review your cart" className="mt-5">
                  <ul className="list-disc space-y-1 pl-5">
                    {blocking.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                  <Link to="/cart" className="mt-2 inline-block underline underline-offset-4">
                    Go to your cart
                  </Link>
                </Alert>
              )}

              {place.isError && (
                <Alert tone="danger" title={errorMessage(place.error)} className="mt-5">
                  {issues.length > 0 && (
                    <ul className="list-disc space-y-1 pl-5">
                      {issues.map((issue) => (
                        <li key={issue}>{issue}</li>
                      ))}
                    </ul>
                  )}
                  {placeError?.code === 'PRICE_CHANGED' && (
                    <p>The summary above now shows the updated total.</p>
                  )}
                </Alert>
              )}

              {placed && (placed.payment_error ?? flow.message) && (
                <Alert
                  tone={flow.phase === 'failed' || placed.payment_error ? 'danger' : 'info'}
                  className="mt-5"
                  title={flow.message ?? placed.payment_error ?? undefined}
                >
                  <p>
                    Order {placed.order.reference} is saved and your pieces are reserved.{' '}
                    <Link
                      to={`/order-confirmation/${placed.order.reference}`}
                      className="underline underline-offset-4"
                    >
                      View order
                    </Link>
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    className="mt-3"
                    loading={flow.busy}
                    onClick={() => {
                      flow.payAgain(placed.order.reference);
                    }}
                  >
                    Try payment again
                  </Button>
                </Alert>
              )}

              <label className="mt-6 flex items-start gap-3 text-sm">
                <input
                  id="checkout-terms"
                  type="checkbox"
                  className="mt-0.5 size-4 shrink-0 accent-ink"
                  aria-invalid={errors.terms ? true : undefined}
                  aria-describedby={errors.terms ? 'checkout-terms-error' : undefined}
                  {...form.register('terms')}
                />
                <span>
                  I agree to the{' '}
                  <Link to="/terms-and-conditions" className="underline underline-offset-4">
                    terms and conditions
                  </Link>{' '}
                  and the{' '}
                  <Link to="/refund-policy" className="underline underline-offset-4">
                    refund policy
                  </Link>
                  .
                </span>
              </label>
              {errors.terms && (
                <p id="checkout-terms-error" className="mt-1.5 text-sm text-danger">
                  {errors.terms.message}
                </p>
              )}

              <Button
                type="submit"
                size="lg"
                className="mt-6 w-full"
                disabled={!canPlace || flow.busy}
                loading={place.isPending || flow.verifying}
              >
                <Lock className="size-4" aria-hidden="true" />
                {totals ? `Place order and pay ${formatMoney(totals.grand_total)}` : 'Place order'}
              </Button>
              <p className="mt-3 text-xs text-ink-muted">
                Payment is handled securely by our payment provider. We never see or store your card
                or bank details. Your pieces are reserved for a limited time once you place the
                order.
              </p>
              {flow.verifying && (
                <p className="mt-2 text-sm" role="status">
                  Confirming your payment…
                </p>
              )}
            </aside>
          </div>
        </form>
      </Container>
    </>
  );
}
