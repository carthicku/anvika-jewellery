import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { components } from '../schema';
import { api, unwrap } from '../client';
import { queryKeys } from '../queryKeys';

export type ProductReviews = components['schemas']['ProductReviewsOut'];
export type MyReviewState = components['schemas']['MyReviewStateOut'];
export type ReviewInput = components['schemas']['ReviewIn'];

/** Approved reviews only (the backend never returns unmoderated ones). */
export function useProductReviews(slug: string, page = 1) {
  return useQuery({
    queryKey: queryKeys.reviews(slug, page),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/products/{slug}/reviews', {
          params: { path: { slug }, query: { page, page_size: 5 } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

/** Whether the signed-in customer may review this piece, and their review if they wrote one. */
export function useMyReview(slug: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.myReview(slug),
    queryFn: () =>
      unwrap(api.GET('/api/v1/products/{slug}/reviews/mine', { params: { path: { slug } } })),
    enabled,
  });
}

export function useSaveReview(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ReviewInput) =>
      unwrap(api.PUT('/api/v1/products/{slug}/reviews/mine', { params: { path: { slug } }, body })),
    onSuccess: (state) => {
      client.setQueryData(queryKeys.myReview(slug), state);
      // An edited review is unpublished until approved again.
      void client.invalidateQueries({ queryKey: ['product', slug, 'reviews'] });
    },
  });
}
