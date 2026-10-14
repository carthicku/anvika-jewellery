import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { Price } from '@/components/ui/Price';
import { formatMoney } from '@/lib/format';
import { availablePrice, card, detail, facets, page } from '@/test/fixtures';
import { mockFetch, renderRoute, requestedUrls } from '@/test/utils';

describe('formatMoney', () => {
  it('formats rupees in Indian style and keeps paise only when present', () => {
    expect(formatMoney('27402.74')).toBe('₹27,402.74');
    expect(formatMoney('1234567.00')).toBe('₹12,34,567');
    expect(formatMoney('13287.00', { paise: true })).toBe('₹13,287.00');
    expect(formatMoney(null)).toBe('');
  });
});

describe('Price', () => {
  it('announces offer and original prices to screen readers', () => {
    render(<Price price={availablePrice('100.50', { compare_at: '120.00' })} />);
    expect(screen.getByText('Offer price', { exact: false })).toHaveClass('sr-only');
    expect(screen.getByText('Original price', { exact: false })).toHaveClass('sr-only');
    expect(screen.getByText('₹120.00', { exact: false })).toBeInTheDocument();
  });

  it('never shows a number when the price is unavailable', () => {
    render(
      <Price
        price={{
          ...availablePrice('0'),
          available: false,
          amount: null,
          unavailable_reason: 'NO_GOLD_RATE',
        }}
      />,
    );
    expect(screen.getByText('Price on request')).toBeInTheDocument();
  });
});

describe('listing filters', () => {
  it('writes filter choices to the URL and refetches with them', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetch({
      'GET /api/v1/products': { body: page([card()]) },
      'GET /api/v1/products/facets': { body: facets },
    });
    const { router } = renderRoute('/collections');
    await user.click(await screen.findByRole('checkbox', { name: /22K/ }));

    await waitFor(() => {
      expect(router.state.location.search).toBe('?purity=22K');
    });
    await waitFor(() => {
      const productCalls = requestedUrls(fetchMock).filter(
        (u) => u.pathname === '/api/v1/products',
      );
      expect(productCalls.at(-1)?.searchParams.getAll('purity')).toEqual(['22K']);
    });
    // The active filter appears as a removable chip; removing it clears the URL.
    await user.click(screen.getByRole('button', { name: 'Remove filter: 22K' }));
    await waitFor(() => {
      expect(router.state.location.search).toBe('');
    });
  });

  it('changes sort order through the URL', async () => {
    const user = userEvent.setup();
    mockFetch({
      'GET /api/v1/products': { body: page([card()]) },
      'GET /api/v1/products/facets': { body: facets },
    });
    const { router } = renderRoute('/collections');
    await user.selectOptions(await screen.findByLabelText('Sort by'), 'price_asc');
    expect(router.state.location.search).toBe('?sort=price_asc');
  });

  it('shows a helpful empty state', async () => {
    mockFetch({
      'GET /api/v1/products': { body: page([]) },
      'GET /api/v1/products/facets': { body: { ...facets, total: 0 } },
    });
    renderRoute('/collections');
    expect(await screen.findByRole('heading', { name: 'No pieces match' })).toBeInTheDocument();
  });
});

describe('product page', () => {
  function setup() {
    mockFetch({
      'GET /api/v1/products/everyday-gold-band': { body: detail },
      'GET /api/v1/products/everyday-gold-band/related': { body: [] },
      'GET /api/v1/products': { body: page([]) },
      'GET /api/v1/shipping/pincode/560001': {
        body: {
          pincode: '560001',
          serviceable: true,
          message: 'Delivery in 4–7 days.',
          options: [
            {
              code: 'standard',
              name: 'Standard delivery',
              description: null,
              fee: '199.00',
              free_above: '25000.00',
              min_days: 4,
              max_days: 7,
              estimated_from: '2026-10-18',
              estimated_to: '2026-10-21',
            },
          ],
        },
      },
    });
    return renderRoute('/products/everyday-gold-band');
  }

  it('shows the default variant with its itemised breakdown', async () => {
    setup();
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Everyday Gold Band' }),
    ).toBeVisible();
    expect(screen.getByRole('radio', { name: '12' })).toBeChecked();
    const table = screen.getByRole('table');
    expect(within(table).getByText('₹24,882.00')).toBeInTheDocument();
    expect(within(table).getByText('− ₹191.40')).toBeInTheDocument();
    expect(within(table).getByText('₹27,402.74')).toBeInTheDocument();
    expect(screen.getByText(/Gold rate used: ₹7,150 per gram/)).toBeInTheDocument();
    // No hallmark section when the product has no verified hallmark data.
    expect(screen.queryByRole('button', { name: /Hallmark/ })).not.toBeInTheDocument();
  });

  it('switching size updates price, SKU and stock status', async () => {
    const user = userEvent.setup();
    setup();
    await user.click(await screen.findByRole('radio', { name: /10/ }));
    expect(screen.getByText('Out of stock')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Specifications' }));
    expect(screen.getByText('ANV-RG-002-10')).toBeInTheDocument();
  });

  it('validates and checks a delivery PIN code', async () => {
    const user = userEvent.setup();
    setup();
    const input = await screen.findByLabelText('Delivery PIN code');
    await user.type(input, '0123');
    await user.click(screen.getByRole('button', { name: 'Check' }));
    expect(screen.getByText('Enter a valid 6-digit PIN code.')).toBeInTheDocument();
    await user.clear(input);
    await user.type(input, '560001');
    await user.click(screen.getByRole('button', { name: 'Check' }));
    expect(await screen.findByText('Standard delivery')).toBeInTheDocument();
  });

  it('saves to and removes from the wishlist', async () => {
    const user = userEvent.setup();
    setup();
    const button = await screen.findByRole('button', { name: 'Save to wishlist' });
    expect(button).toHaveAttribute('aria-pressed', 'false');
    await user.click(button);
    expect(screen.getByRole('button', { name: 'Saved to wishlist' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(window.localStorage.getItem('anvika:wishlist:v1')).toContain('everyday-gold-band');
    expect(screen.getByRole('link', { name: 'Wishlist, 1 saved' })).toBeInTheDocument();
  });
});

describe('contact form', () => {
  it('shows field errors and does not submit invalid data', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetch({});
    renderRoute('/contact');
    await user.click(await screen.findByRole('button', { name: 'Send message' }));
    expect(await screen.findByText('Please enter your name.')).toBeInTheDocument();
    expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument();
    expect(screen.getByLabelText(/^Name/)).toHaveAttribute('aria-invalid', 'true');
    expect(requestedUrls(fetchMock).some((u) => u.pathname === '/api/v1/contact')).toBe(false);
  });
});
