import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { vi } from 'vitest';

import { routes } from '@/router';

export interface MockResponse {
  status?: number;
  body?: unknown;
}

type Handler = MockResponse | ((request: Request) => MockResponse | Promise<MockResponse>);

/**
 * Replace global fetch with a table of handlers keyed by "METHOD /path".
 * Unmatched requests fail loudly so tests never hit the network by accident.
 * Returns the vi mock so tests can inspect the Request objects that were sent.
 */
export function mockFetch(handlers: Record<string, Handler>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request =
      input instanceof Request
        ? input
        : new Request(new URL(String(input), 'http://localhost'), init);
    const url = new URL(request.url, 'http://localhost');
    const key = `${request.method} ${url.pathname}`;
    const handler = handlers[key];
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

export function renderRoute(
  path: string,
): RenderResult & { router: ReturnType<typeof createMemoryRouter> } {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const result = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...result, router };
}
