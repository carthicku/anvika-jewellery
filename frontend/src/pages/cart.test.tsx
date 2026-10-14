import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Cart, CartLine } from '@/api/queries/cart';
import { detail, page } from '@/test/fixtures';
import { mockFetch, renderRoute } from '@/test/utils';

function line(overrides: Partial<CartLine> = {}): CartLine {
  return {
    id: 'l1',
    product_slug: 'everyday-gold-band',
    product_name: 'Everyday Gold Band',
    variant_id: 'v12',
    variant_label: 'Size 12',
    size: '12',
    sku: 'ANV-RG-002-12',
    purity: '22K',
    image: null,
    quantity: 1,
    max_quantity: 8,
    stock_status: 'in_stock',
    unit_price: '27402.74',
    accepted_unit_price: '27402.74',
    price_change: null,
    line_total: '27402.74',
    issue: null,
    ...overrides,
  };
}

function cart(overrides: Partial<Cart> = {}): Cart {
  return {
    lines: [line()],
    item_count: 1,
    totals: {
      subtotal: '26604.60',
      automatic_discount: '0.00',
      coupon_discount: '0.00',
      tax_total: '798.14',
      shipping_fee: '0.00',
      shipping_label: 'Standard delivery',
      free_shipping_above: '25000.00',
      rounding_adjustment: '0.26',
      grand_total: '27403.00',
      breakdown: [
        { key: 'subtotal', label: 'Items (before tax)', amount: '26604.60' },
        { key: 'tax', label: 'GST', amount: '798.14' },
        { key: 'shipping', label: 'Shipping', amount: '0.00' },
        { key: 'rounding', label: 'Rounding adjustment', amount: '0.26' },
        { key: 'total', label: 'Total', amount: '27403.00' },
      ],
    },
    coupon: null,
    can_checkout: true,
    blocking_issues: [],
    notices: [],
    ...overrides,
  };
}

describe('product page add to cart', () => {
  it('adds the selected size and updates the header count', async () => {
    const user = userEvent.setup();
    let sent: unknown = null;
    mockFetch({
      'GET /api/v1/products/everyday-gold-band': { body: detail },
      'GET /api/v1/products/everyday-gold-band/related': { body: [] },
      'GET /api/v1/products': { body: page([]) },
      'POST /api/v1/cart/items': async (request) => {
        sent = await request.json();
        return { body: cart({ item_count: 2, lines: [line({ quantity: 2 })] }) };
      },
    });
    renderRoute('/products/everyday-gold-band');
    const panel = (await screen.findByRole('group', { name: 'Quantity' }))
      .parentElement as HTMLElement;
    await user.click(within(panel).getByRole('button', { name: 'Increase quantity' }));
    await user.click(within(panel).getByRole('button', { name: 'Add to cart' }));
    await waitFor(() => {
      expect(sent).toEqual({ variant_id: 'v12', quantity: 2 });
    });
    expect(await screen.findByRole('link', { name: 'Cart, 2 items' })).toBeInTheDocument();
    // Only variant id and quantity are sent — never a price.
    expect(JSON.stringify(sent)).not.toContain('price');
  });

  it('does not offer add to cart for a sold-out size', async () => {
    const user = userEvent.setup();
    mockFetch({
      'GET /api/v1/products/everyday-gold-band': { body: detail },
      'GET /api/v1/products/everyday-gold-band/related': { body: [] },
      'GET /api/v1/products': { body: page([]) },
    });
    renderRoute('/products/everyday-gold-band');
    await user.click(await screen.findByRole('radio', { name: /10/ }));
    expect(screen.queryByRole('button', { name: 'Add to cart' })).not.toBeInTheDocument();
    expect(screen.getByText(/currently out of stock/)).toBeInTheDocument();
  });
});

describe('cart page', () => {
  it('shows the backend breakdown and line details', async () => {
    mockFetch({ 'GET /api/v1/cart': { body: cart() } });
    renderRoute('/cart');
    expect(await screen.findByRole('link', { name: 'Everyday Gold Band' })).toBeInTheDocument();
    const summary = screen.getByRole('table', { name: 'Price summary' });
    expect(within(summary).getByText('₹27,403.00')).toBeInTheDocument();
    expect(within(summary).getByText('Free')).toBeInTheDocument();
    expect(screen.getByText(/SKU ANV-RG-002-12/)).toBeInTheDocument();
  });

  it('asks the customer to accept a price increase', async () => {
    const user = userEvent.setup();
    let accepted = false;
    mockFetch({
      'GET /api/v1/cart': {
        body: cart({
          can_checkout: false,
          lines: [line({ unit_price: '28000.00', price_change: 'increased' })],
          blocking_issues: [
            'The price of Everyday Gold Band has gone up from ₹27,402.74 to ₹28,000. Please review and accept the updated prices.',
          ],
        }),
      },
      'POST /api/v1/cart/accept-prices': () => {
        accepted = true;
        return { body: cart() };
      },
    });
    renderRoute('/cart');
    expect(await screen.findByText('Price increased')).toBeInTheDocument();
    expect(screen.getByText(/has gone up/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Accept updated prices' }));
    await waitFor(() => {
      expect(accepted).toBe(true);
    });
    await waitFor(() => {
      expect(screen.queryByText('Price increased')).not.toBeInTheDocument();
    });
  });

  it('explains why a coupon was rejected', async () => {
    const user = userEvent.setup();
    mockFetch({
      'GET /api/v1/cart': { body: cart() },
      'POST /api/v1/cart/coupon': {
        status: 422,
        body: { error: { code: 'COUPON_EXPIRED', message: 'This coupon has expired.' } },
      },
    });
    renderRoute('/cart');
    await user.type(await screen.findByLabelText('Coupon code'), 'expired10');
    expect(screen.getByLabelText('Coupon code')).toHaveValue('EXPIRED10');
    await user.click(screen.getByRole('button', { name: 'Apply' }));
    expect(await screen.findByText('This coupon has expired.')).toBeInTheDocument();
  });

  it('shows an empty state', async () => {
    mockFetch({});
    renderRoute('/cart');
    expect(await screen.findByRole('heading', { name: 'Your cart is empty' })).toBeInTheDocument();
  });
});
