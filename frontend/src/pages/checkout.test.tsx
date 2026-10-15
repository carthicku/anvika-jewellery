import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Cart } from '@/api/queries/cart';
import type { CheckoutQuote, Order } from '@/api/queries/orders';
import { mockFetch, renderRoute } from '@/test/utils';

const CART: Cart = {
  lines: [
    {
      id: 'l1',
      product_slug: 'om-pendant',
      product_name: 'Om Pendant',
      variant_id: 'v1',
      variant_label: 'One size',
      size: null,
      sku: 'ANV-PD-001',
      purity: '22K',
      image: null,
      quantity: 1,
      max_quantity: 9,
      stock_status: 'in_stock',
      unit_price: '18431.00',
      accepted_unit_price: '18431.00',
      price_change: null,
      line_total: '18431.00',
      issue: null,
    },
  ],
  item_count: 1,
  totals: {
    subtotal: '17894.17',
    automatic_discount: '0.00',
    coupon_discount: '0.00',
    tax_total: '536.83',
    shipping_fee: '199.00',
    shipping_label: 'Standard delivery',
    free_shipping_above: '25000.00',
    rounding_adjustment: '0.00',
    grand_total: '18630.00',
    breakdown: [
      { key: 'subtotal', label: 'Items (before tax)', amount: '17894.17' },
      { key: 'tax', label: 'GST', amount: '536.83' },
      { key: 'shipping', label: 'Shipping', amount: '199.00' },
      { key: 'total', label: 'Total', amount: '18630.00' },
    ],
  },
  coupon: null,
  can_checkout: true,
  blocking_issues: [],
  notices: [],
};

const QUOTE: CheckoutQuote = {
  cart: CART,
  pincode: '560001',
  serviceable: true,
  message: null,
  shipping_method: 'standard',
  shipping_options: [
    {
      code: 'standard',
      name: 'Standard delivery',
      description: null,
      fee: '199.00',
      free_above: '25000.00',
      min_days: 4,
      max_days: 7,
      estimated_from: '2026-10-19',
      estimated_to: '2026-10-22',
    },
  ],
};

const ADDRESS = {
  full_name: 'Asha Rao',
  phone: '+919876543210',
  line1: '12 MG Road',
  line2: null,
  landmark: null,
  city: 'Bengaluru',
  state: 'Karnataka',
  pincode: '560001',
  country: 'IN',
};

function order(overrides: Partial<Order> = {}): Order {
  return {
    reference: 'ANV-261015-ABC234',
    status: 'pending_payment',
    status_label: 'Awaiting payment',
    payment_status: 'unpaid',
    payment_status_label: 'Not paid',
    created_at: '2026-10-15T06:00:00Z',
    paid_at: null,
    payment_expires_at: '2026-10-15T06:30:00Z',
    email: 'guest@example.com',
    customer_name: 'Asha Rao',
    phone: '+919876543210',
    shipping_address: ADDRESS,
    billing_address: ADDRESS,
    shipping_method: {
      code: 'standard',
      name: 'Standard delivery',
      min_days: 4,
      max_days: 7,
      estimated_from: '2026-10-19',
      estimated_to: '2026-10-22',
    },
    coupon_code: null,
    customer_note: null,
    items: [
      {
        position: 0,
        product_name: 'Om Pendant',
        product_slug: 'om-pendant',
        variant_label: 'One size',
        sku: 'ANV-PD-001',
        purity: '22K',
        image: null,
        quantity: 1,
        unit_price: '18431.00',
        line_discount: '0.00',
        line_tax: '536.83',
        line_total: '18431.00',
      },
    ],
    totals: {
      subtotal: '17894.17',
      automatic_discount: '0.00',
      coupon_discount: '0.00',
      tax_total: '536.83',
      shipping_total: '199.00',
      rounding_adjustment: '0.00',
      grand_total: '18630.00',
      breakdown: CART.totals?.breakdown ?? [],
    },
    timeline: [
      {
        kind: 'order_created',
        title: 'Order placed — awaiting payment',
        note: null,
        created_at: '2026-10-15T06:00:00Z',
      },
    ],
    shipments: [],
    refunds: [],
    can_pay: true,
    can_cancel: true,
    payment_message: null,
    returns: [],
    returnable_items: [],
    ...overrides,
  };
}

const PAYMENT = {
  provider: 'simulator' as const,
  key_id: 'sim_test_key',
  provider_order_id: 'order_sim_1',
  amount_paise: 1863000,
  currency: 'INR',
  store_name: 'Anvika',
  description: 'Order ANV-261015-ABC234',
  prefill: { name: 'Asha Rao', email: 'guest@example.com', contact: '+919876543210' },
};

async function fillGuestForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText(/^Email\*?$/), 'guest@example.com');
  await user.type(screen.getByLabelText(/^Full name/), 'Asha Rao');
  await user.type(screen.getByLabelText(/^Mobile number/), '9876543210');
  await user.type(screen.getByLabelText(/^House/), '12 MG Road');
  await user.type(screen.getByLabelText(/^PIN code/), '560001');
  await user.type(screen.getByLabelText(/^City/), 'Bengaluru');
  await user.selectOptions(screen.getByLabelText(/^State/), 'Karnataka');
  await waitFor(() => {
    expect(screen.getByRole('radio', { name: /Standard delivery/ })).toBeChecked();
  });
  await user.click(screen.getByRole('checkbox', { name: /I agree to the terms/ }));
}

// Filling a whole address form with userEvent takes a few seconds in jsdom.
describe('checkout', { timeout: 20_000 }, () => {
  it('places an order with the quoted total, pays with the simulator and shows the confirmation', async () => {
    const user = userEvent.setup();
    const sent: { body: Record<string, unknown>; key: string | null }[] = [];
    let verifyToken: string | null = null;
    const fetchMock = mockFetch({
      'GET /api/v1/cart': { body: CART },
      'POST /api/v1/checkout/quote': { body: QUOTE },
      'POST /api/v1/checkout/orders': async (request) => {
        sent.push({
          body: (await request.json()) as Record<string, unknown>,
          key: request.headers.get('Idempotency-Key'),
        });
        return {
          body: {
            order: order(),
            access_token: 'guest-token-123',
            payment: PAYMENT,
            payment_error: null,
          },
        };
      },
      'POST /api/v1/payments/simulator/pay': {
        body: {
          provider_order_id: 'order_sim_1',
          provider_payment_id: 'pay_sim_1',
          signature: 'sig',
          status: 'captured',
        },
      },
      'POST /api/v1/payments/verify': (request) => {
        verifyToken = request.headers.get('X-Order-Access-Token');
        const paid = order({
          status: 'confirmed',
          status_label: 'Confirmed',
          payment_status: 'paid',
          payment_status_label: 'Paid',
          can_pay: false,
        });
        return { body: { outcome: 'paid', message: 'Payment received', order: paid } };
      },
      'GET /api/v1/orders/ANV-261015-ABC234': {
        body: order({
          status: 'confirmed',
          status_label: 'Confirmed',
          payment_status: 'paid',
          payment_status_label: 'Paid',
          can_pay: false,
        }),
      },
    });
    const { router } = renderRoute('/checkout');

    expect(await screen.findByRole('button', { name: 'Place order' })).toBeDisabled();
    await fillGuestForm(user);
    await user.click(screen.getByRole('button', { name: 'Place order and pay ₹18,630' }));

    const dialog = await screen.findByRole('dialog', { name: 'Simulated payment' });
    expect(within(dialog).getByText(/no money moves/)).toBeInTheDocument();
    expect(sent).toHaveLength(1);
    const first = sent[0];
    expect(first?.key).toMatch(/^[A-Za-z0-9_-]{16,64}$/);
    expect(first?.body).toEqual({
      email: 'guest@example.com',
      shipping_address: {
        full_name: 'Asha Rao',
        phone: '9876543210',
        line1: '12 MG Road',
        line2: null,
        landmark: null,
        city: 'Bengaluru',
        state: 'Karnataka',
        pincode: '560001',
      },
      billing_address: null,
      shipping_method: 'standard',
      expected_total: '18630.00', // consent to the quoted total — the server re-prices
      terms_accepted: true,
      customer_note: null,
    });

    await user.click(within(dialog).getByRole('button', { name: 'Pay (simulated)' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/order-confirmation/ANV-261015-ABC234');
    });
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Thank you — your order is confirmed' }),
    ).toBeInTheDocument();
    expect(verifyToken).toBe('guest-token-123');
    expect(fetchMock).toHaveBeenCalled();
  });

  it('explains a changed total and reuses the same idempotency key for an identical retry', async () => {
    const user = userEvent.setup();
    const keys: (string | null)[] = [];
    mockFetch({
      'GET /api/v1/cart': { body: CART },
      'POST /api/v1/checkout/quote': { body: QUOTE },
      'POST /api/v1/checkout/orders': (request) => {
        keys.push(request.headers.get('Idempotency-Key'));
        return {
          status: 409,
          body: {
            error: {
              code: 'PAYMENT_PROVIDER_ERROR',
              message: 'We couldn’t reach the payment provider.',
            },
          },
        };
      },
    });
    renderRoute('/checkout');
    await fillGuestForm(user);
    const place = screen.getByRole('button', { name: 'Place order and pay ₹18,630' });
    await user.click(place);
    expect(await screen.findByText('We couldn’t reach the payment provider.')).toBeInTheDocument();
    await user.click(place);
    await waitFor(() => {
      expect(keys).toHaveLength(2);
    });
    expect(keys[0]).toBe(keys[1]);
  });

  it('shows the server’s price-change message', async () => {
    const user = userEvent.setup();
    mockFetch({
      'GET /api/v1/cart': { body: CART },
      'POST /api/v1/checkout/quote': { body: QUOTE },
      'POST /api/v1/checkout/orders': {
        status: 409,
        body: {
          error: {
            code: 'PRICE_CHANGED',
            message:
              'The total has changed to ₹18,900. Please review the updated total before paying.',
            details: { grand_total: '18900.00' },
          },
        },
      },
    });
    renderRoute('/checkout');
    await fillGuestForm(user);
    await user.click(screen.getByRole('button', { name: 'Place order and pay ₹18,630' }));
    expect(await screen.findByText(/The total has changed to ₹18,900/)).toBeInTheDocument();
    expect(screen.getByText('The summary above now shows the updated total.')).toBeInTheDocument();
  });

  it('blocks ordering and focuses the problem when required details are missing', async () => {
    const user = userEvent.setup();
    mockFetch({
      'GET /api/v1/cart': { body: CART },
      'POST /api/v1/checkout/quote': { body: QUOTE },
    });
    renderRoute('/checkout');
    await user.type(await screen.findByLabelText(/^PIN code/), '560001');
    const place = await screen.findByRole('button', { name: 'Place order and pay ₹18,630' });
    await user.click(place);
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument();
    expect(screen.getByText('Please accept the terms to place your order.')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText(/^Email\*?$/)).toHaveFocus();
    });
  });

  it('opens checkout from the cart when the cart is ready', async () => {
    mockFetch({ 'GET /api/v1/cart': { body: CART } });
    renderRoute('/cart');
    expect(await screen.findByRole('link', { name: 'Proceed to checkout' })).toHaveAttribute(
      'href',
      '/checkout',
    );
  });
});

describe('returns', { timeout: 20_000 }, () => {
  it('asks for a return of a delivered piece and shows the request', async () => {
    const user = userEvent.setup();
    const delivered = order({
      status: 'delivered',
      status_label: 'Delivered',
      payment_status: 'paid',
      payment_status_label: 'Paid',
      can_pay: false,
      can_cancel: false,
      returnable_items: [
        {
          position: 0,
          product_name: 'Om Pendant',
          variant_label: 'One size',
          quantity: 1,
          kinds: ['return', 'exchange'],
          deadline: '2026-10-30T10:00:00Z',
        },
      ],
    });
    let body: unknown = null;
    mockFetch({
      'GET /api/v1/orders/ANV-261015-ABC234': { body: delivered },
      'POST /api/v1/orders/ANV-261015-ABC234/returns': async (request) => {
        body = await request.json();
        return {
          status: 201,
          body: {
            ...delivered,
            returnable_items: [],
            returns: [
              {
                id: 'r1',
                kind: 'return',
                kind_label: 'Return for a refund',
                status: 'requested',
                status_label: 'Requested — waiting for our reply',
                reason: 'Not what I expected',
                store_note: null,
                items: [
                  {
                    position: 0,
                    product_name: 'Om Pendant',
                    variant_label: 'One size',
                    quantity: 1,
                  },
                ],
                created_at: '2026-10-16T10:00:00Z',
                updated_at: '2026-10-16T10:00:00Z',
              },
            ],
          },
        };
      },
    });
    renderRoute('/order-confirmation/ANV-261015-ABC234');
    await user.click(await screen.findByRole('button', { name: 'Request a return or exchange' }));
    const dialog = await screen.findByRole('dialog', { name: 'Return or exchange' });
    const send = within(dialog).getByRole('button', { name: 'Send request' });
    expect(send).toBeDisabled();
    await user.selectOptions(within(dialog).getByLabelText('Om Pendant (One size)'), '1');
    await user.type(within(dialog).getByLabelText(/^Reason/), 'Not what I expected');
    await user.click(send);
    expect(await screen.findByText('Requested — waiting for our reply')).toBeVisible();
    expect(body).toEqual({
      kind: 'return',
      reason: 'Not what I expected',
      items: [{ position: 0, quantity: 1 }],
    });
    expect(screen.queryByRole('button', { name: 'Request a return or exchange' })).toBeNull();
  });
});
