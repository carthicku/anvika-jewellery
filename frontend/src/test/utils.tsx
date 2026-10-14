import { QueryClient } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { vi } from 'vitest';

import { AppProviders } from '@/app/AppProviders';
import { routes } from '@/router';

import { home, settings } from './fixtures';

export interface MockResponse {
  status?: number;
  body?: unknown;
}

type Handler = MockResponse | ((request: Request) => MockResponse | Promise<MockResponse>);

/** Responses every page needs (layout header/footer), overridable per test. */
const DEFAULTS: Record<string, Handler> = {
  'GET /api/v1/settings/public': { body: settings },
  'GET /api/v1/categories': { body: home.categories },
};

/**
 * Replace global fetch with a table of handlers keyed by "METHOD /path" (query strings ignored).
 * Unmatched requests fail loudly so tests never hit the network by accident.
 * Returns the vi mock so tests can inspect the Request objects that were sent.
 */
export function mockFetch(handlers: Record<string, Handler>, { defaults = true } = {}) {
  const table = defaults ? { ...DEFAULTS, ...handlers } : handlers;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request =
      input instanceof Request
        ? input
        : new Request(new URL(String(input), 'http://localhost'), init);
    const url = new URL(request.url, 'http://localhost');
    const key = `${request.method} ${url.pathname}`;
    const handler = table[key];
    if (!handler) throw new Error(`Unexpected request in test: ${key}`);
    const result = typeof handler === 'function' ? await handler(request) : handler;
    return new Response(result.body === undefined ? null : JSON.stringify(result.body), {
      status: result.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    });
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

/** Requests the mock received, as URL objects (handy for checking query parameters). */
export function requestedUrls(fetchMock: ReturnType<typeof mockFetch>): URL[] {
  return fetchMock.mock.calls.map(
    ([input]) => new URL(input instanceof Request ? input.url : String(input), 'http://localhost'),
  );
}

export function renderRoute(
  path: string,
): RenderResult & { router: ReturnType<typeof createMemoryRouter> } {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const result = render(
    <AppProviders client={client}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return { ...result, router };
}
