import { useEffect, useRef } from 'react';
import { Link, Outlet, useLocation } from 'react-router';

import { env } from '@/lib/env';

/**
 * Site frame: skip link, header, main landmark, footer.
 * On client-side navigation, focus moves to <main> so keyboard and screen-reader users land on the
 * new page instead of staying on the link they activated (docs/design/ACCESSIBILITY.md).
 */
export function RootLayout() {
  const mainRef = useRef<HTMLElement>(null);
  const { pathname } = useLocation();
  const firstRender = useRef(true);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    mainRef.current?.focus();
    window.scrollTo({ top: 0 });
  }, [pathname]);

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-sm focus:bg-ink focus:px-4 focus:py-2 focus:text-ivory"
      >
        Skip to content
      </a>
      <header className="border-b border-line bg-ivory">
        <div className="mx-auto flex h-16 max-w-7xl items-center px-4 sm:px-6 lg:px-8">
          <Link to="/" className="font-display text-2xl tracking-wide">
            {env.storeName}
          </Link>
        </div>
      </header>
      <main id="main" ref={mainRef} tabIndex={-1} className="flex-1 outline-none">
        <Outlet />
      </main>
      <footer className="bg-noir text-noir-ink">
        <div className="mx-auto max-w-7xl px-4 py-10 text-sm sm:px-6 lg:px-8">
          © {new Date().getFullYear()} {env.storeName}
        </div>
      </footer>
    </div>
  );
}
