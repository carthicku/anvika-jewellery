/**
 * Returns and exchanges on the order page: the customer's requests and their progress, and a form
 * to ask for a new one. Which items qualify (and until when) comes from the backend.
 */
import { useState } from 'react';

import { useRequestReturn, type Order } from '@/api/queries/orders';
import { Button } from '@/components/ui/Button';
import { DialogClose, DialogContent, DialogRoot } from '@/components/ui/Dialog';
import { Alert, Badge } from '@/components/ui/Feedback';
import { FormField, Select, Textarea } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toaster';
import { cn } from '@/lib/cn';
import { formatDateTime, formatShortDate } from '@/lib/format';
import { errorMessage } from '@/lib/forms';

type Kind = 'return' | 'exchange';
type ReturnRequest = Order['returns'][number];

const TONES: Record<ReturnRequest['status'], 'info' | 'success' | 'neutral' | 'warning'> = {
  requested: 'warning',
  approved: 'info',
  rejected: 'neutral',
  received: 'info',
  refunded: 'success',
  closed: 'success',
};

function RequestReturn({ order }: { order: Order }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<Kind>('return');
  const [reason, setReason] = useState('');
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const request = useRequestReturn();
  const { notify } = useToast();
  const kinds = (['return', 'exchange'] as const).filter((k) =>
    order.returnable_items.some((i) => i.kinds.includes(k)),
  );
  const items = order.returnable_items.filter((i) => i.kinds.includes(kind));
  const chosen = items
    .map((i) => ({ position: i.position, quantity: quantities[i.position] ?? 0 }))
    .filter((line) => line.quantity > 0);

  return (
    <DialogRoot
      open={open}
      onOpenChange={(value) => {
        setOpen(value);
        if (!value) request.reset();
      }}
    >
      <Button
        variant="secondary"
        onClick={() => {
          setKind(kinds[0] ?? 'return');
          setOpen(true);
        }}
      >
        Request a return or exchange
      </Button>
      <DialogContent
        title="Return or exchange"
        description="Choose the pieces and tell us why. We'll reply by email, usually within two working days."
      >
        <form
          className="space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            request.mutate(
              { reference: order.reference, body: { kind, reason: reason.trim(), items: chosen } },
              {
                onSuccess: () => {
                  setOpen(false);
                  setQuantities({});
                  setReason('');
                  notify('Your request has been sent.', 'success');
                },
              },
            );
          }}
        >
          {request.isError && <Alert tone="danger" title={errorMessage(request.error)} />}
          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium">What would you like?</legend>
            {kinds.map((k) => (
              <label
                key={k}
                className={cn(
                  'flex cursor-pointer gap-3 rounded-md border p-3 text-sm',
                  kind === k ? 'border-ink' : 'border-line',
                )}
              >
                <input
                  type="radio"
                  name="return-kind"
                  className="mt-0.5 size-4 accent-ink"
                  checked={kind === k}
                  onChange={() => {
                    setKind(k);
                  }}
                />
                <span>
                  {k === 'return' ? 'Return for a refund' : 'Exchange (for example, another size)'}
                </span>
              </label>
            ))}
          </fieldset>
          <fieldset className="space-y-3">
            <legend className="mb-2 text-sm font-medium">Pieces</legend>
            {items.map((item) => (
              <FormField
                key={item.position}
                label={`${item.product_name} (${item.variant_label})`}
                hint={`Request by ${formatShortDate(item.deadline)}`}
              >
                <Select
                  value={quantities[item.position] ?? 0}
                  onChange={(e) => {
                    const quantity = Number(e.target.value);
                    setQuantities((q) => ({ ...q, [item.position]: quantity }));
                  }}
                >
                  {Array.from({ length: item.quantity + 1 }, (_, n) => (
                    <option key={n} value={n}>
                      {n === 0 ? 'Not this piece' : `${String(n)} of ${String(item.quantity)}`}
                    </option>
                  ))}
                </Select>
              </FormField>
            ))}
          </fieldset>
          <FormField label="Reason" required hint="At least 10 characters.">
            <Textarea
              rows={3}
              minLength={10}
              maxLength={500}
              required
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
              }}
            />
          </FormField>
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <DialogClose asChild>
              <Button variant="ghost" type="button">
                Not now
              </Button>
            </DialogClose>
            <Button
              type="submit"
              loading={request.isPending}
              disabled={chosen.length === 0 || reason.trim().length < 10}
            >
              Send request
            </Button>
          </div>
        </form>
      </DialogContent>
    </DialogRoot>
  );
}

/** Renders only when the order has requests or something can still be returned. */
export function OrderReturns({ order }: { order: Order }) {
  if (order.returns.length === 0 && order.returnable_items.length === 0) return null;
  return (
    <section aria-labelledby="returns-heading" className="space-y-4">
      <h2 id="returns-heading" className="font-display text-2xl">
        Returns and exchanges
      </h2>
      {order.returns.length > 0 && (
        <ul className="space-y-3">
          {order.returns.map((r) => (
            <li key={r.id} className="rounded-md border border-line p-4 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">{r.kind_label}</p>
                <Badge tone={TONES[r.status]}>{r.status_label}</Badge>
              </div>
              <p className="mt-1 text-ink-muted">
                {r.items
                  .map((i) => `${i.product_name} (${i.variant_label}) × ${String(i.quantity)}`)
                  .join('; ')}
              </p>
              {r.store_note && <p className="mt-2">Note from us: {r.store_note}</p>}
              <p className="mt-1 text-xs text-ink-muted">
                Requested <time dateTime={r.created_at}>{formatDateTime(r.created_at)}</time>
              </p>
            </li>
          ))}
        </ul>
      )}
      {order.returnable_items.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-ink-muted">
            Some pieces in this order can be returned or exchanged until{' '}
            {formatShortDate(
              order.returnable_items
                .map((i) => i.deadline)
                .sort()
                .at(-1) ?? '',
            )}
            .
          </p>
          <RequestReturn order={order} />
        </div>
      )}
    </section>
  );
}
