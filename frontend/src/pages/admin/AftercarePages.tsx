/**
 * Admin after-sales: return/exchange requests and review moderation. Every decision is made and
 * checked by the backend (state machine, permissions, refund limits); this page only collects it.
 */
import { useState } from 'react';
import { Link, useParams } from 'react-router';

import {
  useAdminReturn,
  useAdminReturns,
  useAdminReviews,
  useModerateReview,
  useReturnAction,
  type AdminReturn,
  type AdminReturnRow,
  type AdminReview,
} from '@/api/queries/admin';
import {
  AdminPage,
  DataTable,
  FormDialog,
  Pager,
  Panel,
  field,
  usePageParam,
} from '@/components/admin/AdminUI';
import { Stars } from '@/components/product/Reviews';
import { Button } from '@/components/ui/Button';
import { Badge, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { FormField, Input, Select, Textarea } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toaster';
import { formatDateTime, formatMoney, hasPaise } from '@/lib/format';

const RETURN_STATUSES = [
  ['', 'All'],
  ['requested', 'Requested'],
  ['approved', 'Approved'],
  ['received', 'Received'],
  ['refunded', 'Refunded'],
  ['closed', 'Completed'],
  ['rejected', 'Rejected'],
] as const;

function money(value: string) {
  return formatMoney(value, { paise: hasPaise(value) });
}

const RETURN_COLUMNS = [
  {
    header: 'Request',
    cell: (r: AdminReturnRow) => (
      <Link
        to={`/admin/returns/${r.id}`}
        className="font-medium underline-offset-4 hover:underline"
      >
        {r.kind === 'return' ? 'Return' : 'Exchange'} · {r.order_reference}
      </Link>
    ),
    className: 'whitespace-nowrap',
  },
  { header: 'Customer', cell: (r: AdminReturnRow) => r.customer_name },
  {
    header: 'Status',
    cell: (r: AdminReturnRow) => (
      <Badge tone={r.status === 'requested' ? 'warning' : 'neutral'}>{r.status_label}</Badge>
    ),
  },
  { header: 'Pieces', cell: (r: AdminReturnRow) => r.item_count, className: 'text-right' },
  {
    header: 'Requested',
    cell: (r: AdminReturnRow) => formatDateTime(r.created_at),
    className: 'whitespace-nowrap',
  },
];

export function AdminReturnsPage() {
  const [page, setPage] = usePageParam();
  const [status, setStatus] = useState('requested');
  const returns = useAdminReturns({ status, page });
  return (
    <AdminPage
      title="Returns"
      description="Customers can ask for a return or exchange after delivery, within each piece's return window."
    >
      <FormField label="Status" className="mb-4 w-48">
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          {RETURN_STATUSES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </FormField>
      <DataTable
        caption="Return requests"
        columns={RETURN_COLUMNS}
        rows={returns.data?.items}
        rowKey={(r) => r.id}
        loading={returns.isPending}
        error={returns.error}
        empty="No requests here."
      />
      {returns.data && (
        <Pager
          page={page}
          pages={returns.data.pages}
          total={returns.data.total}
          onChange={setPage}
        />
      )}
    </AdminPage>
  );
}

function ReturnActions({ data }: { data: AdminReturn }) {
  const action = useReturnAction(data.id);
  const { notify } = useToast();
  const can = (name: string) => data.allowed_actions.includes(name);
  const done = (message: string) => () => {
    notify(message, 'success');
  };
  return (
    <div className="flex flex-wrap gap-2">
      {can('approve') && (
        <FormDialog
          trigger={(open) => <Button onClick={open}>Approve…</Button>}
          title="Approve this request"
          description="The customer is emailed. Add return instructions if useful."
          submitLabel="Approve"
          onSubmit={(form) =>
            action
              .mutateAsync({ action: 'approve', note: field(form, 'note') })
              .then(done('Request approved.'))
          }
        >
          <FormField label="Message to the customer" hint="Optional">
            <Textarea name="note" rows={3} maxLength={500} />
          </FormField>
        </FormDialog>
      )}
      {can('reject') && (
        <FormDialog
          trigger={(open) => (
            <Button variant="secondary" onClick={open}>
              Reject…
            </Button>
          )}
          title="Reject this request"
          description="The customer sees this reason on their order and in the email."
          submitLabel="Reject request"
          danger
          onSubmit={(form) =>
            action
              .mutateAsync({ action: 'reject', note: field(form, 'note') })
              .then(done('Request rejected.'))
          }
        >
          <FormField label="Reason" required>
            <Textarea name="note" rows={3} minLength={3} maxLength={500} required />
          </FormField>
        </FormDialog>
      )}
      {can('receive') && (
        <FormDialog
          trigger={(open) => <Button onClick={open}>Mark as received…</Button>}
          title="Items received"
          description="Tick the pieces that can be sold again; they go back into stock."
          submitLabel="Save"
          onSubmit={(form) =>
            action
              .mutateAsync({
                action: 'receive',
                restock_positions: form.getAll('restock').map(Number),
                note: field(form, 'note'),
              })
              .then(done('Marked as received.'))
          }
        >
          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium">Put back into stock</legend>
            {data.items.map((i) => (
              <label key={i.position} className="flex gap-3 text-sm">
                <input
                  type="checkbox"
                  name="restock"
                  value={i.position}
                  className="mt-0.5 size-4 accent-ink"
                />
                <span>
                  {i.product_name} · {i.variant_label} × {i.quantity}
                  <span className="block text-xs text-ink-muted">{i.sku}</span>
                </span>
              </label>
            ))}
          </fieldset>
          <FormField label="Message to the customer" hint="Optional">
            <Textarea name="note" rows={2} maxLength={500} />
          </FormField>
        </FormDialog>
      )}
      {can('refund') && (
        <FormDialog
          trigger={(open) => <Button onClick={open}>Refund {money(data.suggested_refund)}…</Button>}
          title="Refund the returned pieces"
          description="This records a refund request. Send it to the payment provider from the order page."
          submitLabel="Request refund"
          onSubmit={(form) =>
            action
              .mutateAsync({
                action: 'refund',
                amount: field(form, 'amount'),
                note: field(form, 'note'),
              })
              .then(done('Refund requested.'))
          }
        >
          <FormField
            label="Amount (₹)"
            required
            hint="Suggested: what was paid for these pieces, excluding delivery."
          >
            <Input
              name="amount"
              inputMode="decimal"
              defaultValue={data.suggested_refund}
              pattern="\d+(\.\d{1,2})?"
              required
            />
          </FormField>
          <FormField label="Message to the customer" hint="Optional">
            <Textarea name="note" rows={2} maxLength={500} />
          </FormField>
        </FormDialog>
      )}
      {can('close') && (
        <FormDialog
          trigger={(open) => (
            <Button variant="secondary" onClick={open}>
              Complete…
            </Button>
          )}
          title="Complete without a refund"
          description="For an exchange that has been sent out, or items that were never returned."
          submitLabel="Complete"
          onSubmit={(form) =>
            action
              .mutateAsync({ action: 'close', note: field(form, 'note') })
              .then(done('Request completed.'))
          }
        >
          <FormField label="What happened" required>
            <Textarea name="note" rows={3} minLength={3} maxLength={500} required />
          </FormField>
        </FormDialog>
      )}
    </div>
  );
}

export function AdminReturnDetailPage() {
  const { id = '' } = useParams();
  const query = useAdminReturn(id);
  if (query.isPending) return <Skeleton className="h-96" />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  const r = query.data;
  return (
    <AdminPage
      title={`${r.kind === 'return' ? 'Return' : 'Exchange'} for ${r.order_reference}`}
      description={`${r.status_label} · requested ${formatDateTime(r.created_at)}`}
      actions={
        <Link to="/admin/returns" className="text-sm underline underline-offset-4">
          All returns
        </Link>
      }
    >
      <div className="mb-6">
        <ReturnActions data={r} />
      </div>
      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <div className="min-w-0 space-y-6">
          <Panel title="Pieces">
            <ul className="divide-y divide-line text-sm">
              {r.items.map((i) => (
                <li key={i.position} className="flex justify-between gap-4 py-2">
                  <span>
                    {i.product_name} · {i.variant_label} × {i.quantity}
                    <span className="block text-xs text-ink-muted">{i.sku}</span>
                  </span>
                  {i.restock !== null && (
                    <Badge tone={i.restock ? 'success' : 'neutral'}>
                      {i.restock ? 'Restocked' : 'Not restocked'}
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          </Panel>
          <Panel title="Customer's reason">
            <p className="text-sm whitespace-pre-line">{r.reason}</p>
            {r.store_note && (
              <p className="mt-3 text-sm text-ink-muted">
                Last message to customer: {r.store_note}
              </p>
            )}
          </Panel>
        </div>
        <div className="space-y-6">
          <Panel title="Order">
            <p className="text-sm">
              <Link
                to={`/admin/orders/${r.order_reference}`}
                className="font-medium underline underline-offset-4"
              >
                {r.order_reference}
              </Link>
              <br />
              {r.customer_name}
              <br />
              {r.email}
            </p>
            <p className="mt-2 text-sm text-ink-muted">
              Delivered {r.delivered_at ? formatDateTime(r.delivered_at) : '—'}
            </p>
          </Panel>
          <Panel title="Refund">
            {r.refund_id && r.refund_amount ? (
              <p className="text-sm">
                {money(r.refund_amount)} · <span className="font-medium">{r.refund_status}</span>
                {r.refund_status === 'requested' && (
                  <span className="mt-1 block text-xs text-ink-muted">
                    Send it from the{' '}
                    <Link
                      to={`/admin/orders/${r.order_reference}`}
                      className="underline underline-offset-4"
                    >
                      order page
                    </Link>
                    .
                  </span>
                )}
              </p>
            ) : (
              <p className="text-sm text-ink-muted">
                {r.kind === 'return'
                  ? `None yet. Suggested: ${money(r.suggested_refund)}.`
                  : 'Exchanges are not refunded.'}
              </p>
            )}
          </Panel>
        </div>
      </div>
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- reviews

const REVIEW_STATUSES = [
  ['pending', 'Waiting for approval'],
  ['approved', 'Published'],
  ['rejected', 'Rejected'],
  ['', 'All'],
] as const;

function ReviewCard({ review }: { review: AdminReview }) {
  const moderate = useModerateReview();
  const { notify } = useToast();
  return (
    <li className="rounded-md border border-line bg-surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Stars rating={review.rating} />
        <Badge
          tone={
            review.status === 'pending'
              ? 'warning'
              : review.status === 'approved'
                ? 'success'
                : 'neutral'
          }
        >
          {review.status === 'pending'
            ? 'Waiting'
            : review.status === 'approved'
              ? 'Published'
              : 'Rejected'}
        </Badge>
      </div>
      <p className="mt-2 font-medium">{review.title}</p>
      <p className="mt-1 text-sm whitespace-pre-line">{review.body}</p>
      <p className="mt-2 text-xs text-ink-muted">
        {review.author_name} ({review.customer_email}) ·{' '}
        <Link to={`/products/${review.product_slug}`} className="underline underline-offset-4">
          {review.product_name}
        </Link>{' '}
        · {review.verified_purchase ? 'Verified purchase' : 'Purchase no longer on record'} ·{' '}
        {formatDateTime(review.updated_at)}
      </p>
      {review.moderation_note && (
        <p className="mt-2 text-xs text-ink-muted">Note: {review.moderation_note}</p>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        {review.status !== 'approved' && (
          <Button
            loading={moderate.isPending}
            onClick={() => {
              moderate.mutate(
                { id: review.id, decision: 'approve', note: '' },
                {
                  onSuccess: () => {
                    notify('Review published.', 'success');
                  },
                },
              );
            }}
          >
            Publish
          </Button>
        )}
        {review.status !== 'rejected' && (
          <FormDialog
            trigger={(open) => (
              <Button variant="secondary" onClick={open}>
                {review.status === 'approved' ? 'Unpublish…' : 'Reject…'}
              </Button>
            )}
            title="Don't publish this review"
            description="For staff only; the customer sees that the review wasn't published."
            submitLabel="Reject"
            danger
            onSubmit={(form) =>
              moderate
                .mutateAsync({ id: review.id, decision: 'reject', note: field(form, 'note') })
                .then(() => {
                  notify('Review rejected.', 'success');
                })
            }
          >
            <FormField label="Internal note" hint="Why it was rejected (optional)">
              <Input name="note" maxLength={300} />
            </FormField>
          </FormDialog>
        )}
      </div>
    </li>
  );
}

export function AdminReviewsPage() {
  const [page, setPage] = usePageParam();
  const [status, setStatus] = useState('pending');
  const reviews = useAdminReviews({ status, page });
  return (
    <AdminPage
      title="Reviews"
      description="Only customers with a delivered order can write a review. Nothing appears on the site until it is published here."
    >
      <FormField label="Show" className="mb-4 w-56">
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          {REVIEW_STATUSES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </FormField>
      {reviews.isPending ? (
        <Skeleton className="h-48" />
      ) : reviews.isError ? (
        <ErrorState error={reviews.error} onRetry={() => void reviews.refetch()} />
      ) : reviews.data.items.length === 0 ? (
        <p className="py-6 text-sm text-ink-muted">No reviews here.</p>
      ) : (
        <>
          <ul className="space-y-4">
            {reviews.data.items.map((r) => (
              <ReviewCard key={r.id} review={r} />
            ))}
          </ul>
          <Pager
            page={page}
            pages={reviews.data.pages}
            total={reviews.data.total}
            onChange={setPage}
          />
        </>
      )}
    </AdminPage>
  );
}
