import { CircleCheck, Clock, PackageCheck, Truck } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router';

import { useCancelOrder, type Order } from '@/api/queries/orders';
import { ProductImage } from '@/components/product/ProductImage';
import { Button } from '@/components/ui/Button';
import { DialogClose, DialogContent, DialogRoot } from '@/components/ui/Dialog';
import { Alert, Badge } from '@/components/ui/Feedback';
import { FormField, Textarea } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toaster';
import { formatDateTime, formatMoney, formatShortDate, hasPaise } from '@/lib/format';
import { errorMessage } from '@/lib/forms';

import { PriceSummary } from './PriceSummary';

type Tone = 'neutral' | 'gold' | 'success' | 'warning' | 'danger' | 'info';

const STATUS_TONES: Record<Order['status'], Tone> = {
  pending_payment: 'warning',
  confirmed: 'success',
  processing: 'info',
  shipped: 'info',
  delivered: 'success',
  cancelled: 'neutral',
  expired: 'neutral',
  payment_review: 'warning',
  returned: 'neutral',
};

export function OrderStatusBadge({ order }: { order: Pick<Order, 'status' | 'status_label'> }) {
  return <Badge tone={STATUS_TONES[order.status]}>{order.status_label}</Badge>;
}

function Address({ title, address }: { title: string; address: Order['shipping_address'] }) {
  return (
    <div>
      <h3 className="text-sm font-medium">{title}</h3>
      <address className="mt-2 text-sm leading-relaxed text-ink-muted not-italic">
        {address.full_name}
        <br />
        {address.line1}
        {address.line2 && (
          <>
            <br />
            {address.line2}
          </>
        )}
        {address.landmark && (
          <>
            <br />
            Near {address.landmark}
          </>
        )}
        <br />
        {address.city}, {address.state} {address.pincode}
        <br />
        {address.phone}
      </address>
    </div>
  );
}

function CancelOrder({ order }: { order: Order }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const cancel = useCancelOrder();
  const { notify } = useToast();
  const paid = order.payment_status === 'paid';
  return (
    <DialogRoot
      open={open}
      onOpenChange={(value) => {
        setOpen(value);
        if (!value) cancel.reset();
      }}
    >
      <Button
        variant="secondary"
        onClick={() => {
          setOpen(true);
        }}
      >
        Cancel order
      </Button>
      <DialogContent
        title="Cancel this order?"
        description={
          paid
            ? 'We will cancel your order and request a full refund of the amount you paid. You will get an email when the refund is processed.'
            : 'Your reserved pieces will be released. Nothing has been charged.'
        }
      >
        <form
          className="space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            cancel.mutate(
              { reference: order.reference, reason: reason.trim() || null },
              {
                onSuccess: () => {
                  setOpen(false);
                  notify('Your order has been cancelled.', 'success');
                },
              },
            );
          }}
        >
          {cancel.isError && <Alert tone="danger" title={errorMessage(cancel.error)} />}
          <FormField label="Reason" hint="Optional — helps us improve">
            <Textarea
              rows={3}
              maxLength={300}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
              }}
            />
          </FormField>
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <DialogClose asChild>
              <Button variant="ghost" type="button">
                Keep my order
              </Button>
            </DialogClose>
            <Button type="submit" variant="danger" loading={cancel.isPending}>
              Cancel order
            </Button>
          </div>
        </form>
      </DialogContent>
    </DialogRoot>
  );
}

const TIMELINE_ICONS: Record<string, typeof Clock> = {
  order_confirmed: CircleCheck,
  shipped: Truck,
  delivered: PackageCheck,
};

/** Everything about one order, as the backend reports it. */
export function OrderDetails({
  order,
  onPay,
  paying = false,
}: {
  order: Order;
  onPay?: () => void;
  paying?: boolean;
}) {
  const paise = order.items.some((i) => hasPaise(i.line_total));
  return (
    <div className="grid gap-10 lg:grid-cols-[1fr_22rem] lg:items-start">
      <div className="min-w-0 space-y-10">
        {order.payment_message && (
          <Alert tone={order.status === 'pending_payment' ? 'info' : 'warning'}>
            {order.payment_message}
            {order.can_pay && (
              <span className="mt-1 block">
                Pay by {formatDateTime(order.payment_expires_at)} to keep your pieces reserved.
              </span>
            )}
          </Alert>
        )}
        {(order.can_pay || order.can_cancel) && (
          <div className="flex flex-wrap gap-3">
            {order.can_pay && onPay && (
              <Button loading={paying} onClick={onPay}>
                Pay {formatMoney(order.totals.grand_total)}
              </Button>
            )}
            {order.can_cancel && <CancelOrder order={order} />}
          </div>
        )}

        <section aria-labelledby="items-heading">
          <h2 id="items-heading" className="font-display text-2xl">
            Items
          </h2>
          <ul className="mt-4 divide-y divide-line border-y border-line">
            {order.items.map((item) => (
              <li key={item.sku} className="flex gap-4 py-4">
                <div className="w-20 shrink-0 overflow-hidden rounded-sm bg-surface-muted">
                  {item.image && (
                    <ProductImage
                      image={item.image}
                      sizes="80px"
                      className="aspect-4/5 h-full w-full object-cover"
                    />
                  )}
                </div>
                <div className="flex min-w-0 flex-1 flex-wrap justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium">
                      <Link
                        to={`/products/${item.product_slug}`}
                        className="hover:underline hover:underline-offset-4"
                      >
                        {item.product_name}
                      </Link>
                    </p>
                    <p className="text-sm text-ink-muted">
                      {item.purity} · {item.variant_label} · SKU {item.sku}
                    </p>
                    <p className="tabular text-sm text-ink-muted">
                      {formatMoney(item.unit_price, { paise })} × {item.quantity}
                    </p>
                  </div>
                  <p className="tabular font-medium">{formatMoney(item.line_total, { paise })}</p>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-ink-muted">
            Item totals include GST and any discount. Prices are fixed for this order.
          </p>
        </section>

        <section aria-labelledby="delivery-heading" className="grid gap-6 sm:grid-cols-3">
          <h2 id="delivery-heading" className="sr-only">
            Delivery
          </h2>
          <Address title="Delivery address" address={order.shipping_address} />
          <Address title="Billing address" address={order.billing_address} />
          <div>
            <h3 className="text-sm font-medium">Delivery method</h3>
            <p className="mt-2 text-sm text-ink-muted">
              {order.shipping_method.name}
              <br />
              Estimated {formatShortDate(order.shipping_method.estimated_from)} –{' '}
              {formatShortDate(order.shipping_method.estimated_to)}
            </p>
            {order.shipments.map((s) => (
              <p key={s.tracking_number} className="mt-2 text-sm">
                {s.carrier}:{' '}
                {s.tracking_url ? (
                  <a
                    href={s.tracking_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline underline-offset-4"
                  >
                    {s.tracking_number}
                  </a>
                ) : (
                  s.tracking_number
                )}
              </p>
            ))}
          </div>
        </section>

        <section aria-labelledby="timeline-heading">
          <h2 id="timeline-heading" className="font-display text-2xl">
            Order updates
          </h2>
          <ol className="mt-4 space-y-4 border-l border-line pl-6">
            {order.timeline.map((event, index) => {
              const Icon = TIMELINE_ICONS[event.kind] ?? Clock;
              return (
                <li key={`${event.kind}-${String(index)}`} className="relative">
                  <Icon
                    className="absolute top-0.5 -left-[2.1rem] size-4 bg-ivory text-gold-deep"
                    aria-hidden="true"
                  />
                  <p className="text-sm font-medium">{event.title}</p>
                  {event.note && <p className="text-sm text-ink-muted">{event.note}</p>}
                  <p className="text-xs text-ink-muted">
                    <time dateTime={event.created_at}>{formatDateTime(event.created_at)}</time>
                  </p>
                </li>
              );
            })}
          </ol>
        </section>
      </div>

      <aside
        aria-labelledby="order-summary-heading"
        className="rounded-md border border-line bg-surface p-6 lg:sticky lg:top-32"
      >
        <h2 id="order-summary-heading" className="font-display text-2xl">
          Summary
        </h2>
        <dl className="mt-4 space-y-1 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-ink-muted">Order</dt>
            <dd className="font-medium">{order.reference}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-ink-muted">Placed</dt>
            <dd>{formatDateTime(order.created_at)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-ink-muted">Payment</dt>
            <dd>{order.payment_status_label}</dd>
          </div>
          {order.coupon_code && (
            <div className="flex justify-between gap-4">
              <dt className="text-ink-muted">Coupon</dt>
              <dd>{order.coupon_code}</dd>
            </div>
          )}
        </dl>
        <PriceSummary
          className="mt-5"
          rows={order.totals.breakdown}
          shippingLabel={order.shipping_method.name}
          caption="Order totals"
        />
        {order.refunds.length > 0 && (
          <div className="mt-5 border-t border-line pt-4 text-sm">
            <h3 className="font-medium">Refunds</h3>
            <ul className="mt-2 space-y-1">
              {order.refunds.map((r) => (
                <li key={r.created_at} className="flex justify-between gap-4">
                  <span className="text-ink-muted">
                    {r.status === 'processed' ? 'Refunded' : 'Refund requested'}
                  </span>
                  <span className="tabular">
                    {formatMoney(r.amount, { paise: hasPaise(r.amount) })}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {order.customer_note && (
          <p className="mt-5 border-t border-line pt-4 text-sm text-ink-muted">
            Your note: {order.customer_note}
          </p>
        )}
      </aside>
    </div>
  );
}
