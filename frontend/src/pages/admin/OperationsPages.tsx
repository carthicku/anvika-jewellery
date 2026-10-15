import { useState } from 'react';
import { Link, useParams } from 'react-router';

import {
  useAdjustStock,
  useAdminOrder,
  useAdminOrders,
  useAuditLogs,
  useCreateRate,
  useCustomer,
  useCustomers,
  useDashboard,
  useEnquiries,
  useGoldRates,
  useInventory,
  useMovements,
  useOrderAction,
  usePreviewRate,
  useSetEnquiryStatus,
  useSetThreshold,
  type AdminOrder,
  type AdminOrderRow,
  type InventoryRow,
  type RatePreview,
} from '@/api/queries/admin';
import {
  AdminPage,
  DataTable,
  FormDialog,
  Json,
  Pager,
  Panel,
  StatCard,
  field,
  usePageParam,
} from '@/components/admin/AdminUI';
import { PriceSummary } from '@/components/orders/PriceSummary';
import { Button } from '@/components/ui/Button';
import { Alert, Badge, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { FormField, Input, Select, Textarea } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toaster';
import { cn } from '@/lib/cn';
import { formatDateTime, formatMoney, formatShortDate, hasPaise } from '@/lib/format';
import { errorMessage } from '@/lib/forms';

const ORDER_STATUSES = [
  ['', 'All statuses'],
  ['pending_payment', 'Awaiting payment'],
  ['confirmed', 'Confirmed'],
  ['processing', 'Being prepared'],
  ['shipped', 'Shipped'],
  ['delivered', 'Delivered'],
  ['payment_review', 'Payment review'],
  ['cancelled', 'Cancelled'],
  ['expired', 'Payment not completed'],
] as const;

function money(value: string) {
  return formatMoney(value, { paise: hasPaise(value) });
}

function OrderLink({ reference }: { reference: string }) {
  return (
    <Link
      to={`/admin/orders/${reference}`}
      className="font-medium underline-offset-4 hover:underline"
    >
      {reference}
    </Link>
  );
}

const ORDER_COLUMNS = [
  {
    header: 'Order',
    cell: (o: AdminOrderRow) => <OrderLink reference={o.reference} />,
    className: 'whitespace-nowrap',
  },
  {
    header: 'Placed',
    cell: (o: AdminOrderRow) => formatDateTime(o.created_at),
    className: 'whitespace-nowrap',
  },
  {
    header: 'Customer',
    cell: (o: AdminOrderRow) => (
      <>
        {o.customer_name}
        <span className="block text-xs text-ink-muted">{o.email}</span>
      </>
    ),
  },
  {
    header: 'Status',
    cell: (o: AdminOrderRow) => (
      <>
        <Badge tone={o.status === 'payment_review' ? 'warning' : 'neutral'}>{o.status_label}</Badge>
        <span className="mt-1 block text-xs text-ink-muted">{o.payment_status_label}</span>
      </>
    ),
  },
  { header: 'Items', cell: (o: AdminOrderRow) => o.item_count, className: 'text-right' },
  {
    header: 'Total',
    cell: (o: AdminOrderRow) => <span className="tabular">{money(o.grand_total)}</span>,
    className: 'text-right',
  },
];

/** Fewer columns for the dashboard's narrower panels. */
const COMPACT_ORDER_COLUMNS = [
  ORDER_COLUMNS[0],
  {
    header: 'Customer',
    cell: (o: AdminOrderRow) => (
      <>
        {o.customer_name}
        <span className="block text-xs text-ink-muted">{formatDateTime(o.created_at)}</span>
      </>
    ),
  },
  ORDER_COLUMNS[3],
  ORDER_COLUMNS[5],
].filter((c): c is (typeof ORDER_COLUMNS)[number] => c !== undefined);

// --------------------------------------------------------------------------- dashboard

export function AdminDashboardPage() {
  const dashboard = useDashboard();
  const d = dashboard.data;
  return (
    <AdminPage
      title="Dashboard"
      description={
        d
          ? `Paid orders from ${formatShortDate(d.date_from)} to ${formatShortDate(d.date_to)}. Only verified payments count as revenue.`
          : undefined
      }
    >
      {dashboard.isPending ? (
        <Skeleton className="h-64" />
      ) : dashboard.isError ? (
        <ErrorState error={dashboard.error} onRetry={() => void dashboard.refetch()} />
      ) : !d ? null : (
        <div className="space-y-6">
          {d.gold_rates.some((r) => r.stale || !r.rate_per_gram) && (
            <Alert tone="warning" title="Gold rates need attention">
              {d.gold_rates
                .filter((r) => r.stale || !r.rate_per_gram)
                .map((r) =>
                  r.rate_per_gram
                    ? `${r.purity} was last updated ${String(r.age_hours)} hours ago.`
                    : `${r.purity} has no rate.`,
                )
                .join(' ')}{' '}
              <Link to="/admin/gold-rates" className="underline underline-offset-4">
                Update gold rates
              </Link>
            </Alert>
          )}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Net sales"
              value={formatMoney(d.net_revenue)}
              hint={`${formatMoney(d.paid_revenue)} paid, ${formatMoney(d.refunded)} refunded`}
            />
            <StatCard
              label="Paid orders"
              value={d.paid_orders}
              hint={`${String(d.paid_orders_today)} today`}
            />
            <StatCard label="To fulfil" value={d.to_fulfil} hint="Confirmed or being prepared" />
            <StatCard
              label="Awaiting payment"
              value={d.pending_payment}
              hint="Stock is held until the payment window closes"
            />
          </div>
          {d.review_orders.length > 0 && (
            <Panel title={`Payment review (${String(d.review_orders.length)})`}>
              <p className="mb-3 text-sm text-ink-muted">
                Money was received but the order couldn’t be confirmed automatically. Fulfil or
                refund each one.
              </p>
              <DataTable
                caption="Orders in payment review"
                columns={COMPACT_ORDER_COLUMNS}
                rows={d.review_orders}
                rowKey={(o) => o.reference}
              />
            </Panel>
          )}
          <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
            <Panel
              title="Recent orders"
              actions={
                <Link to="/admin/orders" className="text-sm underline underline-offset-4">
                  All orders
                </Link>
              }
            >
              <DataTable
                caption="Recent orders"
                columns={COMPACT_ORDER_COLUMNS}
                rows={d.recent_orders}
                rowKey={(o) => o.reference}
                empty="No orders yet."
              />
            </Panel>
            <div className="min-w-0 space-y-6">
              <Panel title="Gold rates">
                <ul className="space-y-2 text-sm">
                  {d.gold_rates.map((r) => (
                    <li key={r.purity} className="flex justify-between gap-2">
                      <span>{r.purity}</span>
                      <span className={cn('tabular', r.stale && 'text-warning')}>
                        {r.rate_per_gram
                          ? `${formatMoney(r.rate_per_gram, { paise: true })}/g`
                          : 'Not set'}
                        {r.stale && ' · stale'}
                      </span>
                    </li>
                  ))}
                </ul>
              </Panel>
              <Panel title="Best sellers (paid)">
                {d.best_sellers.length === 0 ? (
                  <p className="text-sm text-ink-muted">No paid orders in this period.</p>
                ) : (
                  <ol className="list-decimal space-y-1 pl-5 text-sm">
                    {d.best_sellers.map((b) => (
                      <li key={b.product_slug}>
                        {b.product_name} <span className="text-ink-muted">× {b.quantity}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </Panel>
              <Panel
                title="Low stock"
                actions={
                  <Link
                    to="/admin/inventory?low=1"
                    className="text-sm underline underline-offset-4"
                  >
                    Inventory
                  </Link>
                }
              >
                {d.low_stock.length === 0 ? (
                  <p className="text-sm text-ink-muted">Nothing is running low.</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {d.low_stock.map((s) => (
                      <li key={s.sku} className="flex justify-between gap-2">
                        <span className="min-w-0 truncate">
                          {s.product_name} · {s.variant_label}
                        </span>
                        <span className={cn('tabular', s.available <= 0 && 'text-danger')}>
                          {s.available}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>
          </div>
        </div>
      )}
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- orders

export function AdminOrdersPage() {
  const [page, setPage] = usePageParam();
  const [status, setStatus] = useState('');
  const [q, setQ] = useState('');
  const [search, setSearch] = useState('');
  const orders = useAdminOrders({ status, q: search, page });
  return (
    <AdminPage title="Orders">
      <form
        className="mb-4 flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(q);
          setPage(1);
        }}
      >
        <FormField label="Status" className="w-48">
          <Select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            {ORDER_STATUSES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField
          label="Search"
          hint="Reference, email, name or phone"
          className="min-w-56 flex-1"
        >
          <Input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
            }}
          />
        </FormField>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>
      <DataTable
        caption="Orders"
        columns={ORDER_COLUMNS}
        rows={orders.data?.items}
        rowKey={(o) => o.reference}
        loading={orders.isPending}
        error={orders.error}
        empty="No orders match."
      />
      {orders.data && (
        <Pager page={page} pages={orders.data.pages} total={orders.data.total} onChange={setPage} />
      )}
    </AdminPage>
  );
}

function OrderActions({ data }: { data: AdminOrder }) {
  const act = useOrderAction();
  const { notify } = useToast();
  const reference = data.order.reference;
  const allowed = new Set(data.allowed_actions);
  const run = (promise: Promise<unknown>, message: string) =>
    promise.then(() => {
      notify(message, 'success');
    });
  const requested = data.refunds.filter((r) => r.status === 'requested');

  return (
    <div className="flex flex-wrap gap-2">
      {allowed.has('start_processing') && (
        <Button
          loading={act.isPending}
          onClick={() => {
            act.mutate(
              { kind: 'status', reference, action: 'start_processing' },
              {
                onSuccess: () => {
                  notify('Marked as being prepared.', 'success');
                },
                onError: (e) => {
                  notify(errorMessage(e), 'error');
                },
              },
            );
          }}
        >
          Start preparing
        </Button>
      )}
      {allowed.has('ship') && (
        <FormDialog
          title="Ship this order"
          description="The customer is emailed the tracking details."
          submitLabel="Mark as shipped"
          trigger={(open) => <Button onClick={open}>Ship…</Button>}
          onSubmit={(form) =>
            run(
              act.mutateAsync({
                kind: 'ship',
                reference,
                carrier: field(form, 'carrier'),
                tracking_number: field(form, 'tracking_number'),
                tracking_url: field(form, 'tracking_url') || null,
              }),
              'Marked as shipped.',
            )
          }
        >
          <FormField label="Courier" required>
            <Input name="carrier" required minLength={2} maxLength={80} />
          </FormField>
          <FormField label="Tracking number" required>
            <Input name="tracking_number" required minLength={3} maxLength={80} />
          </FormField>
          <FormField label="Tracking link" hint="Optional, must start with https://">
            <Input name="tracking_url" type="url" maxLength={500} />
          </FormField>
        </FormDialog>
      )}
      {allowed.has('mark_delivered') && (
        <Button
          loading={act.isPending}
          onClick={() => {
            act.mutate(
              { kind: 'status', reference, action: 'mark_delivered' },
              {
                onError: (e) => {
                  notify(errorMessage(e), 'error');
                },
              },
            );
          }}
        >
          Mark delivered
        </Button>
      )}
      {allowed.has('resolve_confirm') && (
        <FormDialog
          title="Fulfil this order"
          description="Reserves and sells the stock now, then confirms the order and emails the customer."
          submitLabel="Confirm order"
          trigger={(open) => <Button onClick={open}>Confirm and fulfil…</Button>}
          onSubmit={(form) =>
            run(
              act.mutateAsync({
                kind: 'review',
                reference,
                decision: 'confirm',
                note: field(form, 'note'),
              }),
              'Order confirmed.',
            )
          }
        >
          <FormField label="Note" hint="Optional, internal">
            <Input name="note" maxLength={300} />
          </FormField>
        </FormDialog>
      )}
      {allowed.has('resolve_refund') && (
        <FormDialog
          title="Cancel and refund"
          description="Cancels the order and creates a full refund request, which you then send to the payment provider."
          submitLabel="Cancel and request refund"
          danger
          trigger={(open) => (
            <Button variant="secondary" onClick={open}>
              Cancel and refund…
            </Button>
          )}
          onSubmit={(form) =>
            run(
              act.mutateAsync({
                kind: 'review',
                reference,
                decision: 'refund',
                note: field(form, 'note'),
              }),
              'Refund requested.',
            )
          }
        >
          <FormField label="Reason" required>
            <Input name="note" required maxLength={300} />
          </FormField>
        </FormDialog>
      )}
      {allowed.has('cancel') && (
        <FormDialog
          title="Cancel this order"
          description={
            data.order.payment_status === 'paid'
              ? 'Stock is put back and a full refund request is created. The customer is emailed.'
              : 'Reserved stock is released. The customer is emailed.'
          }
          submitLabel="Cancel order"
          danger
          trigger={(open) => (
            <Button variant="secondary" onClick={open}>
              Cancel order…
            </Button>
          )}
          onSubmit={(form) =>
            run(
              act.mutateAsync({ kind: 'cancel', reference, reason: field(form, 'reason') }),
              'Order cancelled.',
            )
          }
        >
          <FormField label="Reason" required>
            <Input name="reason" required minLength={3} maxLength={300} />
          </FormField>
        </FormDialog>
      )}
      {allowed.has('refund') && (
        <FormDialog
          title="Request a refund"
          description={`Up to ${money(data.refundable)} can be refunded. The request is sent to the payment provider in a separate step.`}
          submitLabel="Request refund"
          trigger={(open) => (
            <Button variant="secondary" onClick={open}>
              Refund…
            </Button>
          )}
          onSubmit={(form) =>
            run(
              act.mutateAsync({
                kind: 'refund',
                reference,
                amount: field(form, 'amount'),
                reason: field(form, 'reason'),
              }),
              'Refund requested.',
            )
          }
        >
          <FormField label="Amount (₹)" required>
            <Input
              name="amount"
              required
              inputMode="decimal"
              pattern="^\d+(\.\d{1,2})?$"
              defaultValue={data.refundable}
            />
          </FormField>
          <FormField label="Reason" required>
            <Input name="reason" required minLength={3} maxLength={300} />
          </FormField>
        </FormDialog>
      )}
      {requested.map((r) => (
        <FormDialog
          key={r.id}
          title={`Send refund of ${money(r.amount)}`}
          description="This asks the payment provider to return the money to the customer. With live keys this moves real money and can't be undone."
          submitLabel="Send refund"
          danger
          trigger={(open) => <Button onClick={open}>Send refund {money(r.amount)}…</Button>}
          onSubmit={() =>
            run(
              act.mutateAsync({ kind: 'execute_refund', reference, refund_id: r.id }),
              'Refund sent.',
            )
          }
        />
      ))}
      <FormDialog
        title="Add an internal note"
        description="Visible to staff only."
        submitLabel="Add note"
        trigger={(open) => (
          <Button variant="ghost" onClick={open}>
            Add note…
          </Button>
        )}
        onSubmit={(form) =>
          run(
            act.mutateAsync({ kind: 'note', reference, note: field(form, 'note') }),
            'Note added.',
          )
        }
      >
        <FormField label="Note" required>
          <Textarea name="note" rows={3} required maxLength={500} />
        </FormField>
      </FormDialog>
    </div>
  );
}

export function AdminOrderDetailPage() {
  const { reference = '' } = useParams();
  const query = useAdminOrder(reference);
  if (query.isPending) return <Skeleton className="h-96" />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  const data = query.data;
  const order = data.order;
  const address = order.shipping_address;
  return (
    <AdminPage
      title={`Order ${order.reference}`}
      description={`Placed ${formatDateTime(order.created_at)} · ${order.status_label} · ${order.payment_status_label}`}
      actions={
        <Link to="/admin/orders" className="text-sm underline underline-offset-4">
          All orders
        </Link>
      }
    >
      <div className="mb-6">
        <OrderActions data={data} />
      </div>
      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <div className="min-w-0 space-y-6">
          <Panel title="Items">
            <ul className="divide-y divide-line text-sm">
              {order.items.map((i) => (
                <li key={i.sku} className="flex justify-between gap-4 py-2">
                  <span>
                    {i.product_name} · {i.variant_label}
                    <span className="block text-xs text-ink-muted">
                      {i.sku} · {i.purity} · {money(i.unit_price)} × {i.quantity}
                    </span>
                  </span>
                  <span className="tabular">{money(i.line_total)}</span>
                </li>
              ))}
            </ul>
            <PriceSummary
              className="mt-4"
              rows={order.totals.breakdown}
              shippingLabel={order.shipping_method.name}
              caption="Order totals"
            />
          </Panel>
          <Panel title="Timeline (including internal events)">
            <ol className="space-y-3 text-sm">
              {data.events.map((e, n) => (
                <li key={`${e.kind}-${String(n)}`}>
                  <span className="font-medium">{e.title}</span>{' '}
                  {!e.customer_visible && <Badge>internal</Badge>}
                  <span className="block text-xs text-ink-muted">
                    {formatDateTime(e.created_at)} · {e.actor_type}
                    {e.from_status && e.to_status ? ` · ${e.from_status} → ${e.to_status}` : ''}
                  </span>
                  {e.note && <span className="block text-ink-muted">{e.note}</span>}
                </li>
              ))}
            </ol>
          </Panel>
        </div>
        <div className="space-y-6">
          <Panel title="Customer">
            <p className="text-sm">
              {order.customer_name}
              <br />
              {order.email}
              <br />
              {order.phone}
            </p>
            {data.customer_id && (
              <Link
                to={`/admin/customers/${data.customer_id}`}
                className="mt-2 inline-block text-sm underline underline-offset-4"
              >
                Customer profile
              </Link>
            )}
            <h3 className="mt-4 text-sm font-medium">Deliver to</h3>
            <p className="text-sm text-ink-muted">
              {address.full_name}, {address.line1}
              {address.line2 ? `, ${address.line2}` : ''}, {address.city}, {address.state}{' '}
              {address.pincode}
            </p>
            <p className="mt-2 text-sm">{order.shipping_method.name}</p>
            {order.customer_note && <p className="mt-2 text-sm">Note: {order.customer_note}</p>}
          </Panel>
          <Panel title="Payments">
            {data.payment_attempts.length === 0 ? (
              <p className="text-sm text-ink-muted">No payment attempts.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {data.payment_attempts.map((a) => (
                  <li key={a.provider_order_id}>
                    <span className="font-medium">{a.status}</span> · {a.provider}
                    {a.method ? ` · ${a.method}` : ''}
                    <span className="block text-xs break-all text-ink-muted">
                      {a.provider_order_id}
                      {a.provider_payment_id ? ` / ${a.provider_payment_id}` : ''}
                    </span>
                    {a.error_description && (
                      <span className="block text-xs text-danger">{a.error_description}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title="Refunds">
            {data.refunds.length === 0 ? (
              <p className="text-sm text-ink-muted">None.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {data.refunds.map((r) => (
                  <li key={r.id}>
                    {money(r.amount)} · <span className="font-medium">{r.status}</span>
                    <span className="block text-xs text-ink-muted">
                      {r.reason} · {formatDateTime(r.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-xs text-ink-muted">Refundable now: {money(data.refundable)}</p>
          </Panel>
        </div>
      </div>
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- inventory

function StockRowActions({ row }: { row: InventoryRow }) {
  const adjust = useAdjustStock();
  const threshold = useSetThreshold();
  const { notify } = useToast();
  return (
    <div className="flex flex-wrap gap-2">
      <FormDialog
        title={`Adjust stock · ${row.sku}`}
        description={`On hand ${String(row.on_hand)}, reserved for unpaid orders ${String(row.reserved)}. Use a negative number to remove pieces.`}
        submitLabel="Save adjustment"
        trigger={(open) => (
          <Button size="sm" variant="secondary" onClick={open}>
            Adjust…
          </Button>
        )}
        onSubmit={(form) =>
          adjust
            .mutateAsync({
              variantId: row.variant_id,
              delta: Number(field(form, 'delta')),
              note: field(form, 'note'),
            })
            .then(() => {
              notify('Stock updated.', 'success');
            })
        }
      >
        <FormField label="Change (pieces)" required hint="e.g. 5 to add, -1 to remove">
          <Input name="delta" required inputMode="numeric" pattern="^-?[1-9]\d{0,3}$" />
        </FormField>
        <FormField label="Reason" required>
          <Input name="note" required minLength={3} maxLength={300} />
        </FormField>
      </FormDialog>
      <FormDialog
        title={`Low-stock alert · ${row.sku}`}
        submitLabel="Save"
        trigger={(open) => (
          <Button size="sm" variant="ghost" onClick={open}>
            Alert at {row.low_stock_threshold}
          </Button>
        )}
        onSubmit={(form) =>
          threshold.mutateAsync({ variantId: row.variant_id, value: Number(field(form, 'value')) })
        }
      >
        <FormField label="Warn when available is at or below" required>
          <Input
            name="value"
            required
            inputMode="numeric"
            pattern="^\d{1,4}$"
            defaultValue={row.low_stock_threshold}
          />
        </FormField>
      </FormDialog>
    </div>
  );
}

export function AdminInventoryPage() {
  const [page, setPage] = usePageParam();
  const [q, setQ] = useState('');
  const [search, setSearch] = useState('');
  const [lowOnly, setLowOnly] = useState(() =>
    new URLSearchParams(window.location.search).has('low'),
  );
  const rows = useInventory({ q: search, low_only: lowOnly, page });
  const movements = useMovements({ page: 1 });
  return (
    <AdminPage
      title="Inventory"
      description="Available = on hand − reserved for orders awaiting payment. Every change is recorded with your name."
    >
      <form
        className="mb-4 flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(q);
          setPage(1);
        }}
      >
        <FormField label="Search" hint="Product name or SKU" className="min-w-56 flex-1">
          <Input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
            }}
          />
        </FormField>
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="size-4 accent-ink"
            checked={lowOnly}
            onChange={(e) => {
              setLowOnly(e.target.checked);
              setPage(1);
            }}
          />
          Low stock only
        </label>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>
      <DataTable
        caption="Stock levels"
        rows={rows.data?.items}
        rowKey={(r) => r.variant_id}
        loading={rows.isPending}
        error={rows.error}
        columns={[
          {
            header: 'Product',
            cell: (r) => (
              <>
                {r.product_name}
                <span className="block text-xs text-ink-muted">
                  {r.variant_label} · {r.sku} · {r.product_status}
                </span>
              </>
            ),
          },
          { header: 'On hand', cell: (r) => r.on_hand, className: 'text-right' },
          { header: 'Reserved', cell: (r) => r.reserved, className: 'text-right' },
          {
            header: 'Available',
            cell: (r) => (
              <span
                className={cn(r.available <= r.low_stock_threshold && 'font-medium text-warning')}
              >
                {r.available}
              </span>
            ),
            className: 'text-right',
          },
          { header: 'Actions', cell: (r) => <StockRowActions row={r} /> },
        ]}
      />
      {rows.data && (
        <Pager page={page} pages={rows.data.pages} total={rows.data.total} onChange={setPage} />
      )}
      <Panel title="Recent stock movements" className="mt-8">
        <DataTable
          caption="Recent stock movements"
          rows={movements.data?.items}
          rowKey={(m) => `${m.created_at}-${m.sku}-${m.reason}`}
          loading={movements.isPending}
          error={movements.error}
          columns={[
            { header: 'When', cell: (m) => formatDateTime(m.created_at) },
            { header: 'Item', cell: (m) => `${m.product_name} · ${m.sku}` },
            { header: 'Reason', cell: (m) => m.reason.replaceAll('_', ' ') },
            {
              header: 'On hand',
              cell: (m) => (m.delta_on_hand > 0 ? `+${String(m.delta_on_hand)}` : m.delta_on_hand),
              className: 'text-right',
            },
            {
              header: 'Reserved',
              cell: (m) =>
                m.delta_reserved > 0 ? `+${String(m.delta_reserved)}` : m.delta_reserved,
              className: 'text-right',
            },
            {
              header: 'By / order',
              cell: (m) =>
                m.order_reference ? (
                  <OrderLink reference={m.order_reference} />
                ) : (
                  (m.actor_email ?? 'system')
                ),
            },
            { header: 'Note', cell: (m) => m.note ?? '' },
          ]}
        />
      </Panel>
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- gold rates

export function AdminGoldRatesPage() {
  const rates = useGoldRates();
  const preview = usePreviewRate();
  const create = useCreateRate();
  const { notify } = useToast();
  const [purity, setPurity] = useState<'24K' | '22K' | '18K' | '14K'>('22K');
  const [rate, setRate] = useState('');
  const [note, setNote] = useState('');
  const [confirmLarge, setConfirmLarge] = useState(false);
  const [checked, setChecked] = useState<RatePreview | null>(null);
  const validRate = /^\d{1,8}(\.\d{1,2})?$/.test(rate) && Number(rate) > 0;

  return (
    <AdminPage
      title="Gold rates"
      description="Enter the rate per gram you sell at, from the source you trust. Rates are never fetched automatically, and history is kept for audits."
    >
      {rates.isPending ? (
        <Skeleton className="h-40" />
      ) : rates.isError ? (
        <ErrorState error={rates.error} onRetry={() => void rates.refetch()} />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {rates.data.current.map((r) => (
              <StatCard
                key={r.purity}
                label={`${r.purity} per gram`}
                value={r.rate_per_gram ? formatMoney(r.rate_per_gram, { paise: true }) : 'Not set'}
                hint={
                  r.effective_from
                    ? `${r.stale ? 'Stale — ' : ''}since ${formatDateTime(r.effective_from)}`
                    : 'Weight-based pieces of this purity cannot be sold'
                }
              />
            ))}
          </div>
          <Panel title="New rate">
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                if (!validRate) return;
                preview.mutate(
                  { purity, rate_per_gram: rate },
                  {
                    onSuccess: (result) => {
                      setChecked(result);
                      setConfirmLarge(false);
                    },
                  },
                );
              }}
            >
              <div className="grid gap-4 sm:grid-cols-3">
                <FormField label="Purity" required>
                  <Select
                    value={purity}
                    onChange={(e) => {
                      setPurity(e.target.value as typeof purity);
                      setChecked(null);
                    }}
                  >
                    {['24K', '22K', '18K', '14K'].map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </Select>
                </FormField>
                <FormField
                  label="Rate per gram (₹)"
                  required
                  error={rate && !validRate ? 'Enter an amount like 7150.00' : undefined}
                >
                  <Input
                    inputMode="decimal"
                    value={rate}
                    onChange={(e) => {
                      setRate(e.target.value);
                      setChecked(null);
                    }}
                  />
                </FormField>
                <FormField
                  label="Source"
                  required
                  hint="e.g. the association rate you follow, with date"
                >
                  <Input
                    value={note}
                    maxLength={300}
                    onChange={(e) => {
                      setNote(e.target.value);
                    }}
                  />
                </FormField>
              </div>
              <Button
                type="submit"
                variant="secondary"
                loading={preview.isPending}
                disabled={!validRate}
              >
                Preview price changes
              </Button>
              {preview.isError && <Alert tone="danger" title={errorMessage(preview.error)} />}
            </form>
            {checked && (
              <div className="mt-6 space-y-4">
                <p className="text-sm">
                  {checked.current_rate
                    ? `${checked.purity}: ${formatMoney(checked.current_rate, { paise: true })} → ${formatMoney(checked.new_rate, { paise: true })} (${checked.change_percent ?? '0'}%).`
                    : `${checked.purity} has no current rate.`}{' '}
                  {checked.impacts.length} active variants affected.
                </p>
                {checked.needs_confirmation && (
                  <Alert
                    tone="warning"
                    title={`This is more than the ${checked.max_change_percent}% safety limit.`}
                  >
                    <label className="mt-2 flex items-start gap-2">
                      <input
                        type="checkbox"
                        className="mt-0.5 size-4 accent-ink"
                        checked={confirmLarge}
                        onChange={(e) => {
                          setConfirmLarge(e.target.checked);
                        }}
                      />
                      I have checked this rate and want to apply a {checked.change_percent}% change.
                    </label>
                  </Alert>
                )}
                <DataTable
                  caption="Price impact"
                  rows={checked.impacts.slice(0, 50)}
                  rowKey={(i) => i.sku}
                  empty="No active weight-based pieces of this purity."
                  columns={[
                    { header: 'Piece', cell: (i) => `${i.product_name} · ${i.variant_label}` },
                    {
                      header: 'Now',
                      cell: (i) => (i.old_price ? money(i.old_price) : '—'),
                      className: 'text-right tabular',
                    },
                    {
                      header: 'New',
                      cell: (i) => money(i.new_price),
                      className: 'text-right tabular',
                    },
                  ]}
                />
                <Button
                  disabled={note.trim().length < 3 || (checked.needs_confirmation && !confirmLarge)}
                  loading={create.isPending}
                  onClick={() => {
                    create.mutate(
                      {
                        purity,
                        rate_per_gram: rate,
                        source_note: note.trim(),
                        confirm_large_change: confirmLarge,
                      },
                      {
                        onSuccess: () => {
                          notify(`${purity} rate saved. Prices updated.`, 'success');
                          setChecked(null);
                          setRate('');
                        },
                        onError: (e) => {
                          notify(errorMessage(e), 'error');
                        },
                      },
                    );
                  }}
                >
                  Save new {purity} rate
                </Button>
                {note.trim().length < 3 && (
                  <p className="text-xs text-ink-muted">Add the source before saving.</p>
                )}
              </div>
            )}
          </Panel>
          <Panel title="History">
            <DataTable
              caption="Gold rate history"
              rows={rates.data.history}
              rowKey={(r) => r.id}
              columns={[
                { header: 'Effective from', cell: (r) => formatDateTime(r.effective_from) },
                { header: 'Purity', cell: (r) => r.purity },
                {
                  header: 'Rate / g',
                  cell: (r) => formatMoney(r.rate_per_gram, { paise: true }),
                  className: 'text-right tabular',
                },
                { header: 'Source', cell: (r) => r.source_note },
              ]}
            />
          </Panel>
        </div>
      )}
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- customers & enquiries

export function AdminCustomersPage() {
  const [page, setPage] = usePageParam();
  const [q, setQ] = useState('');
  const [search, setSearch] = useState('');
  const customers = useCustomers({ q: search, page });
  return (
    <AdminPage title="Customers">
      <form
        className="mb-4 flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(q);
          setPage(1);
        }}
      >
        <FormField label="Search" hint="Name, email or phone" className="min-w-56 flex-1">
          <Input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
            }}
          />
        </FormField>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>
      <DataTable
        caption="Customers"
        rows={customers.data?.items}
        rowKey={(c) => c.id}
        loading={customers.isPending}
        error={customers.error}
        columns={[
          {
            header: 'Name',
            cell: (c) => (
              <Link
                to={`/admin/customers/${c.id}`}
                className="font-medium underline-offset-4 hover:underline"
              >
                {c.full_name}
              </Link>
            ),
          },
          { header: 'Email', cell: (c) => c.email },
          { header: 'Joined', cell: (c) => formatShortDate(c.created_at) },
          { header: 'Orders', cell: (c) => c.order_count, className: 'text-right' },
          { header: 'Paid', cell: (c) => money(c.paid_total), className: 'text-right tabular' },
          {
            header: 'Status',
            cell: (c) =>
              c.is_active ? (c.email_verified ? 'Verified' : 'Unverified') : 'Deactivated',
          },
        ]}
      />
      {customers.data && (
        <Pager
          page={page}
          pages={customers.data.pages}
          total={customers.data.total}
          onChange={setPage}
        />
      )}
    </AdminPage>
  );
}

export function AdminCustomerDetailPage() {
  const { id = '' } = useParams();
  const query = useCustomer(id);
  if (query.isPending) return <Skeleton className="h-64" />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  const { customer, addresses, orders } = query.data;
  return (
    <AdminPage
      title={customer.full_name}
      description={`${customer.email} · joined ${formatShortDate(customer.created_at)}`}
    >
      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <Panel title="Orders">
          <DataTable
            caption="Customer orders"
            rows={orders}
            rowKey={(o) => o.reference}
            empty="No orders."
            columns={[
              { header: 'Order', cell: (o) => <OrderLink reference={o.reference} /> },
              { header: 'Placed', cell: (o) => formatShortDate(o.created_at) },
              { header: 'Status', cell: (o) => o.status_label },
              {
                header: 'Total',
                cell: (o) => money(o.grand_total),
                className: 'text-right tabular',
              },
            ]}
          />
        </Panel>
        <Panel title="Addresses">
          {addresses.length === 0 ? (
            <p className="text-sm text-ink-muted">No saved addresses.</p>
          ) : (
            <ul className="space-y-3 text-sm">
              {addresses.map((a) => (
                <li key={a.id}>
                  {a.full_name}, {a.line1}, {a.city}, {a.state} {a.pincode}
                  <span className="block text-xs text-ink-muted">{a.phone}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </AdminPage>
  );
}

export function AdminEnquiriesPage() {
  const [page, setPage] = usePageParam();
  const [status, setStatus] = useState('new');
  const enquiries = useEnquiries({ status, page });
  const setEnquiryStatus = useSetEnquiryStatus();
  return (
    <AdminPage title="Enquiries" description="Messages sent through the contact form.">
      <FormField label="Show" className="mb-4 w-48">
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="new">New</option>
          <option value="in_progress">In progress</option>
          <option value="closed">Closed</option>
          <option value="">All</option>
        </Select>
      </FormField>
      {enquiries.isPending ? (
        <Skeleton className="h-40" />
      ) : enquiries.isError ? (
        <ErrorState error={enquiries.error} onRetry={() => void enquiries.refetch()} />
      ) : enquiries.data.items.length === 0 ? (
        <p className="text-sm text-ink-muted">No enquiries.</p>
      ) : (
        <ul className="space-y-4">
          {enquiries.data.items.map((e) => (
            <li key={e.id}>
              <Panel
                title={e.subject}
                actions={
                  <Select
                    aria-label={`Status of enquiry from ${e.name}`}
                    value={e.status}
                    className="w-40"
                    onChange={(ev) => {
                      setEnquiryStatus.mutate({
                        id: e.id,
                        status: ev.target.value as 'new' | 'in_progress' | 'closed',
                      });
                    }}
                  >
                    <option value="new">New</option>
                    <option value="in_progress">In progress</option>
                    <option value="closed">Closed</option>
                  </Select>
                }
              >
                <p className="text-sm text-ink-muted">
                  {e.name} ·{' '}
                  <a href={`mailto:${e.email}`} className="underline underline-offset-4">
                    {e.email}
                  </a>
                  {e.phone ? ` · ${e.phone}` : ''} · {formatDateTime(e.created_at)}
                </p>
                <p className="mt-2 text-sm whitespace-pre-wrap">{e.message}</p>
              </Panel>
            </li>
          ))}
        </ul>
      )}
      {enquiries.data && (
        <Pager
          page={page}
          pages={enquiries.data.pages}
          total={enquiries.data.total}
          onChange={setPage}
        />
      )}
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- audit

export function AdminAuditPage() {
  const [page, setPage] = usePageParam();
  const [entity, setEntity] = useState('');
  const logs = useAuditLogs({ entity_type: entity, page });
  return (
    <AdminPage
      title="Audit log"
      description="Every admin change, with who made it and when. Entries can't be edited."
    >
      <FormField label="Area" className="mb-4 w-56">
        <Select
          value={entity}
          onChange={(e) => {
            setEntity(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Everything</option>
          {[
            'order',
            'product',
            'variant',
            'gold_rate',
            'discount',
            'coupon',
            'settings',
            'user',
            'category',
            'collection',
            'shipping_method',
            'shipping_zone',
            'content_page',
            'enquiry',
          ].map((t) => (
            <option key={t} value={t}>
              {t.replaceAll('_', ' ')}
            </option>
          ))}
        </Select>
      </FormField>
      <DataTable
        caption="Audit log"
        rows={logs.data?.items}
        rowKey={(l) => l.id}
        loading={logs.isPending}
        error={logs.error}
        columns={[
          { header: 'When', cell: (l) => formatDateTime(l.created_at) },
          { header: 'Who', cell: (l) => l.actor_email ?? l.actor_role ?? 'system' },
          { header: 'Action', cell: (l) => l.action },
          { header: 'Item', cell: (l) => <span className="break-all">{l.entity_id}</span> },
          {
            header: 'Details',
            cell: (l) => (
              <details>
                <summary className="cursor-pointer text-ink-muted">Show</summary>
                <Json value={l.changes} />
              </details>
            ),
          },
        ]}
      />
      {logs.data && (
        <Pager page={page} pages={logs.data.pages} total={logs.data.total} onChange={setPage} />
      )}
    </AdminPage>
  );
}
