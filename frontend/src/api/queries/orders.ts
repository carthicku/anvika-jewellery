import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { components } from '../schema';
import { api, unwrap } from '../client';
import { queryKeys } from '../queryKeys';
import { orderTokenHeaders, saveOrderToken } from '@/lib/orderAccess';

export type Order = components['schemas']['OrderOut'];
export type OrderSummary = components['schemas']['OrderSummaryOut'];
export type CheckoutQuote = components['schemas']['CheckoutQuoteOut'];
export type CreateOrderInput = components['schemas']['CreateOrderIn'];
export type CheckoutOrder = components['schemas']['CheckoutOrderOut'];
export type PaymentResult = components['schemas']['PaymentResultOut'];

/** Delivery options + full breakdown for a PIN code (no side effects on the server). */
export function useCheckoutQuote(pincode: string | null, method: string | null) {
  return useQuery({
    queryKey: queryKeys.checkoutQuote(pincode ?? '', method ?? ''),
    queryFn: () =>
      unwrap(
        api.POST('/api/v1/checkout/quote', {
          body: { pincode: pincode ?? '', shipping_method: method },
        }),
      ),
    enabled: pincode !== null,
    placeholderData: keepPreviousData,
    staleTime: 0,
  });
}

export function usePlaceOrder() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ body, key }: { body: CreateOrderInput; key: string }) =>
      unwrap(
        api.POST('/api/v1/checkout/orders', {
          body,
          params: { header: { 'Idempotency-Key': key } },
        }),
      ),
    onSuccess: (result) => {
      if (result.access_token) saveOrderToken(result.order.reference, result.access_token);
      client.setQueryData(queryKeys.order(result.order.reference), result.order);
    },
  });
}

function usePaymentMutation<TVars extends { reference: string }>(
  fn: (vars: TVars, headers: Record<string, string>) => Promise<PaymentResult>,
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (vars: TVars) => fn(vars, orderTokenHeaders(vars.reference)),
    onSuccess: (result) => {
      client.setQueryData(queryKeys.order(result.order.reference), result.order);
      if (result.outcome === 'paid') {
        void client.invalidateQueries({ queryKey: queryKeys.cart });
        void client.invalidateQueries({ queryKey: queryKeys.orders });
      }
    },
  });
}

export function useVerifyPayment() {
  return usePaymentMutation(
    (
      body: {
        reference: string;
        provider_order_id: string;
        provider_payment_id: string;
        signature: string;
      },
      headers,
    ) => unwrap(api.POST('/api/v1/payments/verify', { body, headers })),
  );
}

export function useReportPaymentFailure() {
  return usePaymentMutation(
    (
      body: { reference: string; provider_order_id: string; provider_payment_id: string | null },
      headers,
    ) => unwrap(api.POST('/api/v1/payments/report-failure', { body, headers })),
  );
}

export function useRetryPayment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (reference: string) =>
      unwrap(
        api.POST('/api/v1/payments/retry', {
          body: { reference },
          headers: orderTokenHeaders(reference),
        }),
      ),
    onSuccess: (result) => {
      client.setQueryData(queryKeys.order(result.order.reference), result.order);
    },
  });
}

/** Development/test only: what the payment pop-up would return. No money moves. */
export function useSimulatorPay() {
  return useMutation({
    mutationFn: (body: {
      reference: string;
      provider_order_id: string;
      outcome: 'success' | 'failure';
    }) =>
      unwrap(
        api.POST('/api/v1/payments/simulator/pay', {
          body,
          headers: orderTokenHeaders(body.reference),
        }),
      ),
  });
}

export function useOrders(page: number, enabled = true) {
  return useQuery({
    queryKey: [...queryKeys.orders, page],
    queryFn: () =>
      unwrap(api.GET('/api/v1/orders', { params: { query: { page, page_size: 10 } } })),
    enabled,
    placeholderData: keepPreviousData,
  });
}

export function useOrder(reference: string) {
  return useQuery({
    queryKey: queryKeys.order(reference),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/orders/{reference}', {
          params: { path: { reference } },
          headers: orderTokenHeaders(reference),
        }),
      ),
    retry: false,
  });
}

export function useCancelOrder() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ reference, reason }: { reference: string; reason: string | null }) =>
      unwrap(
        api.POST('/api/v1/orders/{reference}/cancel', {
          params: { path: { reference } },
          body: { reason },
          headers: orderTokenHeaders(reference),
        }),
      ),
    onSuccess: (order) => {
      client.setQueryData(queryKeys.order(order.reference), order);
      void client.invalidateQueries({ queryKey: queryKeys.orders });
    },
  });
}
