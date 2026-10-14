import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { mockFetch, renderRoute } from '@/test/utils';

describe('routing', () => {
  it('renders the home page with the brand heading', async () => {
    mockFetch({ 'GET /api/v1/health': { body: { status: 'ok', database: 'not_checked' } } });
    renderRoute('/');
    expect(await screen.findByRole('heading', { level: 1, name: 'Anvika' })).toBeInTheDocument();
    expect(await screen.findByText('API connected')).toBeInTheDocument();
  });

  it('shows a helpful message when the API is unreachable', async () => {
    mockFetch({
      'GET /api/v1/health': {
        status: 503,
        body: { error: { code: 'SERVICE_UNAVAILABLE', message: 'down' } },
      },
    });
    renderRoute('/');
    expect(await screen.findByText(/API unreachable/)).toBeInTheDocument();
  });

  it('renders a 404 page for unknown routes with a way back home', async () => {
    renderRoute('/this/does/not/exist');
    expect(
      await screen.findByRole('heading', { level: 1, name: /couldn.t find that page/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Return to the homepage' })).toHaveAttribute(
      'href',
      '/',
    );
  });

  it('offers a skip link to the main content', () => {
    mockFetch({ 'GET /api/v1/health': { body: { status: 'ok' } } });
    renderRoute('/');
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute('href', '#main');
  });
});
