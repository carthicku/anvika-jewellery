/** Central list of TanStack Query keys, so invalidation is consistent across the app. */
import type { ProductQuery } from './queries/catalogue';

export const queryKeys = {
  publicSettings: ['settings', 'public'] as const,
  home: ['home'] as const,
  categories: ['categories'] as const,
  collections: ['collections'] as const,
  listing: (slug: string) => ['listing', slug] as const,
  products: (query: ProductQuery) => ['products', query] as const,
  facets: (query: ProductQuery) => ['facets', query] as const,
  product: (slug: string) => ['product', slug] as const,
  related: (slug: string) => ['product', slug, 'related'] as const,
  suggest: (q: string) => ['suggest', q] as const,
  content: (slug: string) => ['content', slug] as const,
  pincode: (pin: string) => ['pincode', pin] as const,
};
