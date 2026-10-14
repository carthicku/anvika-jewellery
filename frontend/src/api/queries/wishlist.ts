import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';

import { GUEST_WISHLIST_KEY, useLocalList } from '@/hooks/useLocalList';

import { api, unwrap } from '../client';
import { queryKeys } from '../queryKeys';
import { useMe } from './account';

/**
 * One wishlist API for the whole UI:
 *  - guests: product slugs in this browser (useLocalList)
 *  - signed-in customers: the server list (merged with the guest list at sign-in)
 */
export function useWishlist() {
  const me = useMe();
  const signedIn = Boolean(me.data);
  const local = useLocalList(GUEST_WISHLIST_KEY);
  const client = useQueryClient();

  const server = useQuery({
    queryKey: queryKeys.wishlistSlugs,
    queryFn: () => unwrap(api.GET('/api/v1/wishlist/slugs')),
    enabled: signedIn,
  });

  const mutation = useMutation({
    mutationFn: ({ slug, add }: { slug: string; add: boolean }) =>
      add
        ? unwrap(api.PUT('/api/v1/wishlist/{slug}', { params: { path: { slug } } }))
        : unwrap(api.DELETE('/api/v1/wishlist/{slug}', { params: { path: { slug } } })),
    onMutate: async ({ slug, add }) => {
      // Optimistic update so the heart responds instantly; rolled back on error.
      await client.cancelQueries({ queryKey: queryKeys.wishlistSlugs });
      const previous = client.getQueryData<string[]>(queryKeys.wishlistSlugs) ?? [];
      client.setQueryData<string[]>(
        queryKeys.wishlistSlugs,
        add ? [slug, ...previous.filter((s) => s !== slug)] : previous.filter((s) => s !== slug),
      );
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context) client.setQueryData(queryKeys.wishlistSlugs, context.previous);
    },
    onSettled: () => void client.invalidateQueries({ queryKey: queryKeys.wishlist }),
  });

  const slugs = signedIn ? (server.data ?? []) : local.items;
  const { add: addLocal, remove: removeLocal } = local;
  const { mutate } = mutation;

  const toggle = useCallback(
    (slug: string, add: boolean) => {
      if (signedIn) mutate({ slug, add });
      else if (add) addLocal(slug, { toFront: true });
      else removeLocal(slug);
    },
    [signedIn, mutate, addLocal, removeLocal],
  );

  return { slugs, signedIn, has: (slug: string) => slugs.includes(slug), toggle };
}

/** Move a guest wishlist into the account after sign-in, then clear the browser copy. */
export function useMergeGuestWishlist() {
  const local = useLocalList(GUEST_WISHLIST_KEY);
  const client = useQueryClient();
  return useCallback(async () => {
    if (local.items.length === 0) return;
    try {
      await unwrap(
        api.POST('/api/v1/wishlist/merge', { body: { slugs: local.items.slice(0, 50) } }),
      );
      local.clear();
      await client.invalidateQueries({ queryKey: queryKeys.wishlist });
    } catch {
      /* keep the guest list; merging will be retried at the next sign-in */
    }
  }, [local, client]);
}

export function useAccountWishlist(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.wishlistCards,
    queryFn: () => unwrap(api.GET('/api/v1/wishlist')),
    enabled,
  });
}
