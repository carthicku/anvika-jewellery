import { isRouteErrorResponse, Link, useRouteError } from 'react-router';

/** Shown when a route fails to render or load. Never exposes stack traces to shoppers. */
export function RouteErrorPage() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;
  if (import.meta.env.DEV) console.error(error);

  return (
    <main id="main" className="mx-auto max-w-2xl px-4 py-24 text-center sm:px-6">
      <title>{notFound ? 'Page not found' : 'Something went wrong'}</title>
      <h1 className="font-display text-4xl font-medium">
        {notFound ? 'We couldn’t find that page' : 'Something went wrong'}
      </h1>
      <p className="mt-4 text-ink-muted">
        {notFound
          ? 'The link may be outdated.'
          : 'Please refresh the page. If the problem continues, contact us and we will help.'}
      </p>
      <Link
        to="/"
        className="mt-8 inline-flex min-h-11 items-center rounded-sm bg-ink px-6 text-sm font-medium text-ivory"
      >
        Return to the homepage
      </Link>
    </main>
  );
}
