/** Central list of TanStack Query keys, so invalidation is consistent across the app. */
import type { ProductQuery } from './queries/catalogue';

export const queryKeys = {
  me: ['me'] as const,
  cart: ['cart'] as const,
  sessions: ['account', 'sessions'] as const,
  addresses: ['account', 'addresses'] as const,
  wishlist: ['wishlist'] as const,
  wishlistSlugs: ['wishlist', 'slugs'] as const,
  wishlistCards: ['wishlist', 'cards'] as const,
  publicSettings: ['settings', 'public'] as const,
  home: ['home'] as const,
  categories: ['categories'] as const,
  collections: ['collections'] as const,
  listing: (slug: string) => ['listing', slug] as const,
  products: (query: ProductQuery) => ['products', query] as const,
  facets: (query: ProductQuery) => ['facets', query] as const,
  product: (slug: string) => ['product', slug] as const,
  related: (slug: string) => ['product', slug, 'related'] as const,
  reviews: (slug: string, page: number) => ['product', slug, 'reviews', page] as const,
  myReview: (slug: string) => ['product', slug, 'reviews', 'mine'] as const,
  suggest: (q: string) => ['suggest', q] as const,
  content: (slug: string) => ['content', slug] as const,
  pincode: (pin: string) => ['pincode', pin] as const,
  checkoutQuote: (pin: string, method: string) => ['checkout', 'quote', pin, method] as const,
  orders: ['orders'] as const,
  order: (reference: string) => ['order', reference] as const,
};
