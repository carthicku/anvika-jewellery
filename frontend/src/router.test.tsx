import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { home } from '@/test/fixtures';
import { mockFetch, renderRoute } from '@/test/utils';

describe('routing and layout', () => {
  it('renders the home page from API data', async () => {
    mockFetch({ 'GET /api/v1/home': { body: home } });
    renderRoute('/');
    expect(
      await screen.findByRole('heading', { level: 1, name: /gold jewellery/i }),
    ).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Everyday Gold Band' })).toHaveAttribute(
      'href',
      '/products/everyday-gold-band',
    );
    expect(await screen.findByText('Free standard delivery on orders above ₹25,000')).toBeVisible();
  });

  it('shows a retryable error when the home data fails to load', async () => {
    mockFetch({
      'GET /api/v1/home': {
        status: 503,
        body: { error: { code: 'SERVICE_UNAVAILABLE', message: 'Down for a moment.' } },
      },
    });
    renderRoute('/');
    expect(await screen.findByText('Down for a moment.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('renders a 404 page for unknown routes with a way back home', async () => {
    mockFetch({});
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
    mockFetch({ 'GET /api/v1/home': { body: home } });
    renderRoute('/');
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute('href', '#main');
  });

  it('shows placeholders, not invented business facts, in the footer', async () => {
    mockFetch({ 'GET /api/v1/home': { body: home } });
    renderRoute('/');
    expect(await screen.findByText('[Business address — to be configured]')).toBeInTheDocument();
  });
});
