import { ArrowRight, ShoppingBag, Tag, Trash2, X } from 'lucide-react';
import { useState, type SyntheticEvent } from 'react';
import { Link } from 'react-router';

import {
  useAcceptPrices,
  useApplyCoupon,
  useCart,
  useRemoveCartItem,
  useRemoveCoupon,
  useUpdateCartItem,
  type Cart,
  type CartLine,
} from '@/api/queries/cart';
import { Container, PageHeader, PageMeta } from '@/components/layout/Page';
import { ProductImage } from '@/components/product/ProductImage';
import { Button } from '@/components/ui/Button';
import { Alert, Badge, EmptyState, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { QuantityStepper } from '@/components/ui/QuantityStepper';
import { useToast } from '@/components/ui/Toaster';
import { cn } from '@/lib/cn';
import { formatMoney, hasPaise } from '@/lib/format';
import { errorMessage } from '@/lib/forms';

const ISSUE_TEXT: Record<NonNullable<CartLine['issue']>, string> = {
  unavailable: 'No longer available',
  price_unavailable: 'Price unavailable',
  out_of_stock: 'Out of stock',
  insufficient_stock: 'Not enough in stock',
};

function LineItem({ line }: { line: CartLine }) {
  const update = useUpdateCartItem();
  const remove = useRemoveCartItem();
  const { notify } = useToast();
  const href = `/products/${line.product_slug}`;

  return (
    <li className="flex gap-4 py-6 sm:gap-6">
      <Link
        to={href}
        className="block w-24 shrink-0 overflow-hidden rounded-sm bg-surface-muted sm:w-32"
        tabIndex={-1}
        aria-hidden="true"
      >
        {line.image && (
          <ProductImage
            image={line.image}
            sizes="128px"
            className="aspect-4/5 h-full w-full object-cover"
          />
        )}
      </Link>
      <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:justify-between">
        <div className="min-w-0 space-y-1">
          <h2 className="font-medium">
            <Link
              to={href}
              className="hover:underline hover:decoration-gold hover:underline-offset-4"
            >
              {line.product_name}
            </Link>
          </h2>
          <p className="text-sm text-ink-muted">
            {line.purity}
            {line.size ? ` · ${line.variant_label}` : ''} · SKU {line.sku}
          </p>
          <p className="tabular flex flex-wrap items-center gap-2 text-sm">
            {line.unit_price ? formatMoney(line.unit_price) : '—'} each
            {line.price_change === 'increased' && <Badge tone="warning">Price increased</Badge>}
            {line.price_change === 'decreased' && <Badge tone="success">Price dropped</Badge>}
          </p>
          {line.issue && (
            <p className="text-sm text-danger" role="status">
              {ISSUE_TEXT[line.issue]}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 sm:flex-col sm:flex-nowrap sm:items-end">
          <QuantityStepper
            size="sm"
            label={`Quantity of ${line.product_name}`}
            value={line.quantity}
            max={Math.max(line.quantity, line.max_quantity)}
            disabled={update.isPending || line.issue === 'unavailable'}
            onChange={(quantity) => {
              update.mutate(
                { id: line.id, quantity },
                {
                  onError: (error) => {
                    notify(errorMessage(error), 'error');
                  },
                },
              );
            }}
          />
          <p className="tabular font-medium sm:text-right">
            {line.line_total
              ? formatMoney(line.line_total, { paise: hasPaise(line.line_total) })
              : ''}
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto px-2 text-ink-muted sm:ml-0"
            loading={remove.isPending}
            aria-label={`Remove ${line.product_name} from cart`}
            onClick={() => {
              remove.mutate(line.id, {
                onSuccess: () => {
                  notify(`Removed ${line.product_name}`, 'info');
                },
              });
            }}
          >
            <Trash2 className="size-4" aria-hidden="true" />
            <span className="sm:sr-only">Remove</span>
          </Button>
        </div>
      </div>
    </li>
  );
}

function CouponForm({ cart }: { cart: Cart }) {
  const [code, setCode] = useState('');
  const apply = useApplyCoupon();
  const remove = useRemoveCoupon();

  if (cart.coupon) {
    return (
      <div className="rounded-sm border border-line bg-surface-muted/60 p-3 text-sm">
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-2 font-medium">
            <Tag className="size-4 text-gold-deep" aria-hidden="true" />
            {cart.coupon.code}
          </span>
          <button
            type="button"
            onClick={() => {
              remove.mutate();
            }}
            className="inline-flex items-center gap-1 text-ink-muted underline underline-offset-4 hover:text-ink"
            aria-label={`Remove coupon ${cart.coupon.code}`}
          >
            <X className="size-3.5" aria-hidden="true" /> Remove
          </button>
        </div>
        {cart.coupon.message && (
          <p
            className={cn('mt-1', cart.coupon.applied ? 'text-success' : 'text-warning')}
            role="status"
          >
            {cart.coupon.message}
          </p>
        )}
      </div>
    );
  }

  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    if (!code.trim()) return;
    apply.mutate(code.trim(), {
      onSuccess: () => {
        setCode('');
      },
    });
  };

  return (
    <form onSubmit={submit} noValidate>
      <label htmlFor="coupon-code" className="text-sm font-medium">
        Coupon code
      </label>
      <div className="mt-1.5 flex gap-2">
        <input
          id="coupon-code"
          value={code}
          onChange={(e) => {
            setCode(e.target.value.toUpperCase());
            apply.reset();
          }}
          autoComplete="off"
          maxLength={40}
          aria-invalid={apply.isError || undefined}
          aria-describedby={apply.isError ? 'coupon-error' : undefined}
          className="min-h-11 min-w-0 flex-1 rounded-sm border border-line-strong bg-surface px-3 text-sm uppercase"
        />
        <Button type="submit" variant="secondary" loading={apply.isPending}>
          Apply
        </Button>
      </div>
      {apply.isError && (
        <p id="coupon-error" className="mt-1.5 text-sm text-danger">
          {errorMessage(apply.error)}
        </p>
      )}
    </form>
  );
}

function Summary({ cart }: { cart: Cart }) {
  const totals = cart.totals;
  return (
    <section
      aria-labelledby="summary-heading"
      className="rounded-md border border-line bg-surface p-6"
    >
      <h2 id="summary-heading" className="font-display text-2xl">
        Order summary
      </h2>
      <div className="mt-5">
        <CouponForm cart={cart} />
      </div>
      {totals && (
        <>
          <table className="mt-6 w-full text-sm">
            <caption className="sr-only">Price summary</caption>
            <tbody>
              {totals.breakdown.map((row) => {
                const paise = totals.breakdown.some((r) => hasPaise(r.amount));
                const negative = row.amount.startsWith('-');
                return (
                  <tr
                    key={row.key}
                    className={cn(
                      row.key === 'total' && 'border-t border-line text-base font-medium',
                    )}
                  >
                    <th scope="row" className="py-1.5 text-left font-normal">
                      {row.key === 'total'
                        ? 'Total (incl. GST)'
                        : row.key === 'shipping'
                          ? `Shipping (${totals.shipping_label ?? 'estimated'})`
                          : row.label}
                    </th>
                    <td className={cn('tabular py-1.5 text-right', negative && 'text-success')}>
                      {row.key === 'shipping' && row.amount === '0.00'
                        ? 'Free'
                        : negative
                          ? `− ${formatMoney(row.amount.slice(1), { paise })}`
                          : formatMoney(row.amount, { paise })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {totals.free_shipping_above && totals.shipping_fee !== '0.00' && (
            <p className="mt-2 text-xs text-ink-muted">
              Free {totals.shipping_label?.toLowerCase() ?? 'delivery'} on orders above{' '}
              {formatMoney(totals.free_shipping_above)}. Delivery options are confirmed at checkout.
            </p>
          )}
        </>
      )}
      <Button size="lg" className="mt-6 w-full" disabled aria-describedby="checkout-note">
        Proceed to checkout <ArrowRight className="size-4" aria-hidden="true" />
      </Button>
      <p id="checkout-note" className="mt-2 text-xs text-ink-muted">
        {cart.can_checkout
          ? 'Online checkout opens in the next release of this store.'
          : 'Resolve the items highlighted in your cart to continue.'}
      </p>
      <Link
        to="/collections"
        className="mt-4 block text-center text-sm underline underline-offset-4"
      >
        Continue shopping
      </Link>
    </section>
  );
}

export function CartPage() {
  const cart = useCart();
  const accept = useAcceptPrices();
  const data = cart.data;
  const hasIncrease = data?.lines.some((l) => l.price_change === 'increased') ?? false;

  return (
    <>
      <PageMeta title="Your cart" path="/cart" noindex />
      <Container className="pb-24">
        <PageHeader title="Your cart" />
        {cart.isPending ? (
          <div className="grid gap-10 lg:grid-cols-[1fr_24rem]">
            <div className="space-y-6">
              <Skeleton className="h-36" />
              <Skeleton className="h-36" />
            </div>
            <Skeleton className="h-80" />
          </div>
        ) : cart.isError ? (
          <ErrorState error={cart.error} onRetry={() => void cart.refetch()} />
        ) : data && data.lines.length === 0 ? (
          <EmptyState
            icon={ShoppingBag}
            title="Your cart is empty"
            action={
              <Button asChild>
                <Link to="/collections">Explore the collection</Link>
              </Button>
            }
          >
            Pieces you add will appear here, with a full price breakdown.
          </EmptyState>
        ) : data ? (
          <div className="grid gap-10 lg:grid-cols-[1fr_24rem] lg:items-start">
            <div className="min-w-0">
              {data.blocking_issues.length > 0 && (
                <Alert tone="warning" title="Please review your cart" className="mb-6">
                  <ul className="list-disc space-y-1 pl-5">
                    {data.blocking_issues.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                  {hasIncrease && (
                    <Button
                      size="sm"
                      className="mt-3"
                      loading={accept.isPending}
                      onClick={() => {
                        accept.mutate();
                      }}
                    >
                      Accept updated prices
                    </Button>
                  )}
                </Alert>
              )}
              {data.notices.map((notice) => (
                <Alert key={notice} tone="success" className="mb-4">
                  {notice}
                </Alert>
              ))}
              <ul className="divide-y divide-line border-y border-line">
                {data.lines.map((line) => (
                  <LineItem key={line.id} line={line} />
                ))}
              </ul>
              <p className="mt-4 text-xs text-ink-muted">
                Prices include GST and follow the current gold rate. Items are not reserved until
                you place your order.
              </p>
            </div>
            <div className="lg:sticky lg:top-32">
              <Summary cart={data} />
            </div>
          </div>
        ) : null}
      </Container>
    </>
  );
}
