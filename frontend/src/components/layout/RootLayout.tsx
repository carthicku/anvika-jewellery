import { useEffect, useRef } from 'react';
import { Outlet, ScrollRestoration, useLocation } from 'react-router';

import { AnnouncementBar, SiteHeader } from './SiteHeader';
import { SiteFooter } from './SiteFooter';

/**
 * Site frame: skip link, announcement, header, main landmark, footer.
 * On client-side navigation, focus moves to <main> so keyboard and screen-reader users land on the
 * new page instead of staying on the link they activated (docs/design/ACCESSIBILITY.md).
 */
export function RootLayout() {
  const mainRef = useRef<HTMLElement>(null);
  const { pathname } = useLocation();
  // Compare with the previous path (not a "first render" flag): effects may run twice in
  // StrictMode, and focus must only move on a real navigation, never on the initial load.
  const previousPath = useRef(pathname);

  // Publish the sticky header's height as --header-h (used by full-screen sections such as the
  // home hero). It changes with the breakpoint, so it is observed rather than hard-coded.
  useEffect(() => {
    const header = document.querySelector<HTMLElement>('body > #root header');
    if (!header || typeof ResizeObserver === 'undefined') return;
    const publish = () => {
      document.documentElement.style.setProperty('--header-h', `${String(header.offsetHeight)}px`);
    };
    publish();
    const observer = new ResizeObserver(publish);
    observer.observe(header);
    return () => {
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    if (previousPath.current === pathname) return;
    previousPath.current = pathname;
    mainRef.current?.focus({ preventScroll: true });
  }, [pathname]);

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-sm focus:bg-ink focus:px-4 focus:py-2 focus:text-ivory"
      >
        Skip to content
      </a>
      <AnnouncementBar />
      <SiteHeader />
      {/* At least one screen tall: while a page loads, the footer stays below the fold instead of
          being pushed down when content arrives (layout shift). */}
      <main id="main" ref={mainRef} tabIndex={-1} className="min-h-dvh flex-1 outline-none">
        <Outlet />
      </main>
      <SiteFooter />
      <ScrollRestoration />
    </div>
  );
}
