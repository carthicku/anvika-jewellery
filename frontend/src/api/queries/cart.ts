import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { components } from '../schema';
import { api, unwrap } from '../client';
import { queryKeys } from '../queryKeys';

export type Cart = components['schemas']['CartOut'];
export type CartLine = components['schemas']['CartLineOut'];

/** The server-priced cart for this browser / customer. */
export function useCart() {
  return useQuery({
    queryKey: queryKeys.cart,
    queryFn: () => unwrap(api.GET('/api/v1/cart')),
    staleTime: 15_000,
  });
}

/** Every cart mutation returns the freshly priced cart, which replaces the cached one. */
function useCartMutation<TVariables>(fn: (vars: TVariables) => Promise<Cart>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (cart) => {
      client.setQueryData(queryKeys.cart, cart);
    },
  });
}

export function useAddToCart() {
  return useCartMutation((body: { variant_id: string; quantity: number }) =>
    unwrap(api.POST('/api/v1/cart/items', { body })),
  );
}

export function useUpdateCartItem() {
  return useCartMutation(({ id, quantity }: { id: string; quantity: number }) =>
    unwrap(
      api.PATCH('/api/v1/cart/items/{item_id}', {
        params: { path: { item_id: id } },
        body: { quantity },
      }),
    ),
  );
}

export function useRemoveCartItem() {
  return useCartMutation((id: string) =>
    unwrap(api.DELETE('/api/v1/cart/items/{item_id}', { params: { path: { item_id: id } } })),
  );
}

export function useAcceptPrices() {
  return useCartMutation(() => unwrap(api.POST('/api/v1/cart/accept-prices')));
}

export function useApplyCoupon() {
  return useCartMutation((code: string) =>
    unwrap(api.POST('/api/v1/cart/coupon', { body: { code } })),
  );
}

export function useRemoveCoupon() {
  return useCartMutation(() => unwrap(api.DELETE('/api/v1/cart/coupon')));
}
