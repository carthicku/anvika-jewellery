import { Link } from 'react-router';

import { env } from '@/lib/env';

export function NotFoundPage() {
  return (
    <>
      <title>{`Page not found — ${env.storeName}`}</title>
      <meta name="robots" content="noindex" />
      <section className="mx-auto max-w-2xl px-4 py-24 text-center sm:px-6">
        <p className="eyebrow">Error 404</p>
        <h1 className="mt-4 font-display text-4xl font-medium sm:text-5xl">
          We couldn&apos;t find that page
        </h1>
        <p className="mt-4 text-ink-muted">
          The link may be outdated, or the piece may no longer be available.
        </p>
        <Link
          to="/"
          className="mt-8 inline-flex min-h-11 items-center rounded-sm bg-ink px-6 text-sm font-medium text-ivory transition-colors hover:bg-ink/90"
        >
          Return to the homepage
        </Link>
      </section>
    </>
  );
}
