import { useHealth } from '@/api/queries/health';
import { env } from '@/lib/env';

/** Phase 1 home: brand heading plus a development-only API status line. Replaced in Phase 2. */
export function HomePage() {
  return (
    <>
      <title>{`${env.storeName} — Fine Gold Jewellery`}</title>
      <section className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
        <p className="eyebrow">Fine gold jewellery</p>
        <h1 className="mt-4 font-display text-5xl font-medium tracking-tight sm:text-6xl">
          {env.storeName}
        </h1>
        {env.isDev && <ApiStatus />}
      </section>
    </>
  );
}

function ApiStatus() {
  const health = useHealth();
  const label = health.isPending
    ? 'Checking API…'
    : health.isError
      ? 'API unreachable — is the backend running on port 8010?'
      : 'API connected';
  return (
    <p role="status" className="mt-8 text-sm text-ink-muted">
      <span className="sr-only">Development: </span>
      {label}
    </p>
  );
}
