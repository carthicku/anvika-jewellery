import { CircleCheck, Package } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';

import { ApiError } from '@/api/client';
import { useMe } from '@/api/queries/account';
import { useOrder, useOrders, type Order } from '@/api/queries/orders';
import { AccountSection } from '@/components/account/AccountLayout';
import { Container, PageHeader, PageMeta } from '@/components/layout/Page';
import { OrderDetails, OrderStatusBadge } from '@/components/orders/OrderDetails';
import { usePaymentFlow } from '@/components/orders/PaymentFlow';
import { ProductImage } from '@/components/product/ProductImage';
import { Button } from '@/components/ui/Button';
import { Alert, EmptyState, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { Pagination } from '@/components/ui/Pagination';
import { formatMoney, formatShortDate } from '@/lib/format';
import { captureTokenFromHash } from '@/lib/orderAccess';

const HEADINGS: Partial<Record<Order['status'], { title: string; text: string }>> = {
  confirmed: {
    title: 'Thank you — your order is confirmed',
    text: 'We have received your payment and emailed your confirmation.',
  },
  pending_payment: {
    title: 'Complete your payment',
    text: 'Your order is saved and your pieces are reserved for a limited time.',
  },
  payment_review: {
    title: 'We are reviewing your order',
    text: 'Your payment arrived and we need to check something before we confirm.',
  },
  expired: {
    title: 'Payment was not completed',
    text: 'Nothing was charged. You can place a new order from your cart.',
  },
  cancelled: { title: 'This order was cancelled', text: '' },
};

function useOrderWithPayment(reference: string) {
  const order = useOrder(reference);
  const flow = usePaymentFlow(reference, order.data?.totals.grand_total ?? null);
  return { order, flow };
}

function OrderBody({ reference }: { reference: string }) {
  const { order, flow } = useOrderWithPayment(reference);
  if (order.isPending) return <Skeleton className="h-96" />;
  if (order.isError) {
    if (order.error instanceof ApiError && order.error.status === 404) {
      return (
        <EmptyState icon={Package} title="We couldn't find that order">
          If you checked out as a guest, open the link in your confirmation email on this device.
          Signed-in customers can find every order under My account → Orders.
        </EmptyState>
      );
    }
    return <ErrorState error={order.error} onRetry={() => void order.refetch()} />;
  }
  return (
    <>
      {flow.simulatedDialog}
      {flow.message && (
        <Alert tone={flow.phase === 'failed' ? 'danger' : 'info'} className="mb-6">
          {flow.message}
        </Alert>
      )}
      <OrderDetails
        order={order.data}
        paying={flow.busy}
        onPay={() => {
          flow.payAgain(reference);
        }}
      />
    </>
  );
}

/** After checkout (and from the confirmation email link, which carries a guest's private token). */
export function OrderConfirmationPage() {
  const { reference = '' } = useParams();
  // Must run before the first fetch so a guest's emailed link works.
  useState(() => {
    captureTokenFromHash(reference);
    return null;
  });
  const order = useOrder(reference);
  const heading = order.data ? HEADINGS[order.data.status] : undefined;
  const me = useMe();

  return (
    <>
      <PageMeta title={`Order ${reference}`} path={`/order-confirmation/${reference}`} noindex />
      <Container className="pb-24">
        <PageHeader
          eyebrow={`Order ${reference}`}
          title={heading?.title ?? 'Your order'}
          description={heading?.text}
        />
        {order.data?.status === 'confirmed' && (
          <p className="-mt-4 mb-8 flex items-center gap-2 text-sm text-success" role="status">
            <CircleCheck className="size-4" aria-hidden="true" /> Payment received
          </p>
        )}
        <OrderBody reference={reference} />
        <div className="mt-12 flex flex-wrap gap-4">
          <Button asChild variant="secondary">
            <Link to="/collections">Continue shopping</Link>
          </Button>
          {me.data && (
            <Button asChild variant="ghost">
              <Link to="/account/orders">All my orders</Link>
            </Button>
          )}
        </div>
      </Container>
    </>
  );
}

export function AccountOrdersPage() {
  const [params] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  const orders = useOrders(page);
  return (
    <>
      <PageMeta title="My orders" path="/account/orders" noindex />
      <AccountSection title="Orders">
        {orders.isPending ? (
          <div className="space-y-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        ) : orders.isError ? (
          <ErrorState error={orders.error} onRetry={() => void orders.refetch()} />
        ) : orders.data.items.length === 0 ? (
          <EmptyState
            icon={Package}
            title="No orders yet"
            action={
              <Button asChild>
                <Link to="/collections">Explore the collection</Link>
              </Button>
            }
          >
            Orders you place while signed in will appear here.
          </EmptyState>
        ) : (
          <>
            <ul className="divide-y divide-line border-y border-line">
              {orders.data.items.map((o) => (
                <li key={o.reference}>
                  <Link
                    to={`/account/orders/${o.reference}`}
                    className="flex gap-4 py-4 hover:bg-surface-muted/50"
                  >
                    <div className="w-16 shrink-0 overflow-hidden rounded-sm bg-surface-muted">
                      {o.image && (
                        <ProductImage
                          image={o.image}
                          sizes="64px"
                          className="aspect-4/5 h-full w-full object-cover"
                        />
                      )}
                    </div>
                    <div className="flex min-w-0 flex-1 flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-medium">{o.reference}</p>
                        <p className="text-sm text-ink-muted">
                          {formatShortDate(o.created_at)} · {o.first_item_name}
                          {o.item_count > 1 ? ` and ${String(o.item_count - 1)} more` : ''}
                        </p>
                        <div className="mt-1">
                          <OrderStatusBadge order={o} />
                        </div>
                      </div>
                      <p className="tabular font-medium">{formatMoney(o.grand_total)}</p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
            <Pagination page={page} pages={orders.data.pages} />
          </>
        )}
      </AccountSection>
    </>
  );
}

export function AccountOrderDetailPage() {
  const { reference = '' } = useParams();
  const order = useOrder(reference);
  return (
    <>
      <PageMeta title={`Order ${reference}`} path={`/account/orders/${reference}`} noindex />
      <AccountSection
        title={`Order ${reference}`}
        description={order.data ? `Placed ${formatShortDate(order.data.created_at)}` : undefined}
        action={order.data ? <OrderStatusBadge order={order.data} /> : undefined}
      >
        <OrderBody reference={reference} />
        <Link
          to="/account/orders"
          className="mt-10 inline-block text-sm underline underline-offset-4"
        >
          Back to all orders
        </Link>
      </AccountSection>
    </>
  );
}
