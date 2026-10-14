import { createBrowserRouter, type RouteObject } from 'react-router';

import { RootLayout } from '@/components/layout/RootLayout';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { RouteErrorPage } from '@/pages/RouteErrorPage';
import { HomePage } from '@/pages/storefront/HomePage';

/** Editable content pages: URL path → content slug (must match backend app/api/sitemap.py). */
export const CONTENT_ROUTES: Record<string, string> = {
  '/about': 'about',
  '/faq': 'faq',
  '/jewellery-care': 'jewellery-care',
  '/gold-buying-guide': 'gold-buying-guide',
  '/shipping-policy': 'shipping-policy',
  '/returns-and-exchanges': 'returns-and-exchanges',
  '/privacy-policy': 'privacy-policy',
  '/terms-and-conditions': 'terms-and-conditions',
  '/refund-policy': 'refund-policy',
};

/*
 * Route-level code splitting: only the home page ships in the initial bundle; every other page
 * (and heavy dependencies such as the Markdown renderer) loads when first visited.
 */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <RootLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: 'collections',
        lazy: async () => ({
          Component: (await import('@/pages/storefront/ListingPages')).CollectionsPage,
        }),
      },
      {
        path: 'collections/:slug',
        lazy: async () => ({
          Component: (await import('@/pages/storefront/ListingPages')).ListingPage,
        }),
      },
      {
        path: 'search',
        lazy: async () => ({
          Component: (await import('@/pages/storefront/ListingPages')).SearchPage,
        }),
      },
      {
        path: 'products/:slug',
        lazy: async () => ({
          Component: (await import('@/pages/storefront/ProductPage')).ProductPage,
        }),
      },
      {
        path: 'wishlist',
        lazy: async () => ({
          Component: (await import('@/pages/storefront/WishlistPage')).WishlistPage,
        }),
      },
      {
        path: 'cart',
        lazy: async () => ({
          Component: (await import('@/pages/storefront/CartPage')).CartPage,
        }),
      },
      {
        path: 'contact',
        lazy: async () => ({
          Component: (await import('@/pages/storefront/ContactPage')).ContactPage,
        }),
      },
      ...Object.entries(CONTENT_ROUTES).map(([path, slug]): RouteObject => ({
        path: path.slice(1),
        lazy: async () => {
          const { ContentPage } = await import('@/pages/storefront/ContentPage');
          return { element: <ContentPage key={slug} slug={slug} path={path} /> };
        },
      })),
      ...(
        [
          ['login', 'LoginPage'],
          ['register', 'RegisterPage'],
          ['forgot-password', 'ForgotPasswordPage'],
          ['reset-password', 'ResetPasswordPage'],
          ['verify-email', 'VerifyEmailPage'],
        ] as const
      ).map(([path, name]): RouteObject => ({
        path,
        lazy: async () => ({ Component: (await import('@/pages/auth/AuthPages'))[name] }),
      })),
      {
        path: 'account',
        lazy: async () => ({
          Component: (await import('@/components/account/AccountLayout')).AccountLayout,
        }),
        children: [
          {
            index: true,
            lazy: async () => ({
              Component: (await import('@/pages/account/AccountPages')).AccountOverviewPage,
            }),
          },
          ...(
            [
              ['profile', 'ProfilePage'],
              ['addresses', 'AddressesPage'],
              ['wishlist', 'AccountWishlistPage'],
              ['security', 'SecurityPage'],
            ] as const
          ).map(([path, name]): RouteObject => ({
            path,
            lazy: async () => ({ Component: (await import('@/pages/account/AccountPages'))[name] }),
          })),
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
