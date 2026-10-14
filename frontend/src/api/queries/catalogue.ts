import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';

import { api, unwrap } from '../client';
import { queryKeys } from '../queryKeys';

export type SortOption = 'relevance' | 'newest' | 'price_asc' | 'price_desc';

/** Mirrors the backend's /products query parameters (validated again by the backend). */
export interface ProductQuery {
  q?: string;
  category?: string;
  collection?: string;
  purity?: string[];
  metal_colour?: string[];
  min_price?: string;
  max_price?: string;
  in_stock?: boolean;
  attr?: string[];
  slug?: string[];
  sort?: SortOption;
  page?: number;
  page_size?: number;
}

export function usePublicSettings() {
  return useQuery({
    queryKey: queryKeys.publicSettings,
    queryFn: () => unwrap(api.GET('/api/v1/settings/public')),
    staleTime: 5 * 60_000,
  });
}

export function useHome() {
  return useQuery({ queryKey: queryKeys.home, queryFn: () => unwrap(api.GET('/api/v1/home')) });
}

export function useCategories() {
  return useQuery({
    queryKey: queryKeys.categories,
    queryFn: () => unwrap(api.GET('/api/v1/categories')),
    staleTime: 5 * 60_000,
  });
}

export function useCollections() {
  return useQuery({
    queryKey: queryKeys.collections,
    queryFn: () => unwrap(api.GET('/api/v1/collections')),
    staleTime: 5 * 60_000,
  });
}

export function useListing(slug: string) {
  return useQuery({
    queryKey: queryKeys.listing(slug),
    queryFn: () => unwrap(api.GET('/api/v1/listings/{slug}', { params: { path: { slug } } })),
  });
}

export function useProducts(query: ProductQuery, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: queryKeys.products(query),
    queryFn: () => unwrap(api.GET('/api/v1/products', { params: { query } })),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

export function useFacets(query: ProductQuery) {
  // Facets describe the browsing context only, so refinements don't need to be part of the key.
  const context: ProductQuery = {
    q: query.q,
    category: query.category,
    collection: query.collection,
  };
  return useQuery({
    queryKey: queryKeys.facets(context),
    queryFn: () => unwrap(api.GET('/api/v1/products/facets', { params: { query: context } })),
    placeholderData: keepPreviousData,
  });
}

export function useProduct(slug: string) {
  return useQuery({
    queryKey: queryKeys.product(slug),
    queryFn: () => unwrap(api.GET('/api/v1/products/{slug}', { params: { path: { slug } } })),
  });
}

export function useRelated(slug: string) {
  return useQuery({
    queryKey: queryKeys.related(slug),
    queryFn: () =>
      unwrap(api.GET('/api/v1/products/{slug}/related', { params: { path: { slug } } })),
  });
}

export function useSuggestions(q: string) {
  return useQuery({
    queryKey: queryKeys.suggest(q),
    queryFn: () => unwrap(api.GET('/api/v1/search/suggest', { params: { query: { q } } })),
    enabled: q.trim().length >= 2,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}

export function useContentPage(slug: string) {
  return useQuery({
    queryKey: queryKeys.content(slug),
    queryFn: () => unwrap(api.GET('/api/v1/content/{slug}', { params: { path: { slug } } })),
    staleTime: 5 * 60_000,
  });
}

export function usePincodeCheck(pincode: string | null) {
  return useQuery({
    queryKey: queryKeys.pincode(pincode ?? ''),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/shipping/pincode/{pincode}', {
          params: { path: { pincode: pincode ?? '' } },
        }),
      ),
    enabled: pincode !== null,
    staleTime: 10 * 60_000,
  });
}

export function useContactForm() {
  return useMutation({
    mutationFn: (body: {
      name: string;
      email: string;
      phone?: string | null;
      subject: string;
      message: string;
      website: string;
      elapsed_seconds: number;
    }) => unwrap(api.POST('/api/v1/contact', { body })),
  });
}

export function useNewsletterSignup() {
  return useMutation({
    mutationFn: (body: {
      email: string;
      consent: boolean;
      website: string;
      elapsed_seconds: number;
      source: string;
    }) => unwrap(api.POST('/api/v1/newsletter/subscribe', { body })),
  });
}
