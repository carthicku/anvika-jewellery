import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { User } from '@/api/queries/account';
import type { AdminReturn, AdminReview, Dashboard } from '@/api/queries/admin';
import { mockFetch, renderRoute } from '@/test/utils';

const STAFF: User = {
  id: 's1',
  email: 'staff@example.com',
  full_name: 'Priya Staff',
  phone: null,
  role: 'staff',
  email_verified: true,
  permissions: [
    'catalogue:write',
    'content:write',
    'customers:view',
    'dashboard:view',
    'inventory:write',
    'orders:write',
  ],
};

const staff = { 'GET /api/v1/auth/me': { body: { user: STAFF } } };

const DASHBOARD: Dashboard = {
  date_from: '2026-09-16T00:00:00Z',
  date_to: '2026-10-15T00:00:00Z',
  paid_orders: 0,
  paid_revenue: '0.00',
  refunded: '0.00',
  net_revenue: '0.00',
  paid_orders_today: 0,
  pending_payment: 0,
  payment_review: 0,
  to_fulfil: 0,
  open_returns: 1,
  pending_reviews: 2,
  recent_orders: [],
  review_orders: [],
  low_stock: [],
  best_sellers: [],
  gold_rates: [],
};

const RETURN: AdminReturn = {
  id: 'r1',
  order_reference: 'ANV-261015-ABCDEF',
  customer_name: 'Asha Rao',
  email: 'asha@example.com',
  kind: 'return',
  status: 'requested',
  status_label: 'Requested — waiting for our reply',
  item_count: 1,
  reason: 'The ring is too small.',
  store_note: null,
  items: [
    {
      position: 0,
      product_name: 'Lotus Ring',
      variant_label: 'Size 12',
      sku: 'ANV-RG-002-12',
      quantity: 1,
      restock: null,
    },
  ],
  delivered_at: '2026-10-10T10:00:00Z',
  suggested_refund: '25000.00',
  refund_id: null,
  refund_status: null,
  refund_amount: null,
  allowed_actions: ['approve', 'reject'],
  created_at: '2026-10-12T10:00:00Z',
  updated_at: '2026-10-12T10:00:00Z',
};

const REVIEW: AdminReview = {
  id: 'v1',
  product_name: 'Lotus Ring',
  product_slug: 'lotus-ring',
  rating: 4,
  title: 'Lovely',
  body: 'Beautiful finish and it fits well.',
  author_name: 'Asha R.',
  customer_email: 'asha@example.com',
  verified_purchase: true,
  status: 'pending',
  moderation_note: null,
  created_at: '2026-10-12T10:00:00Z',
  updated_at: '2026-10-12T10:00:00Z',
};

describe('admin navigation', () => {
  it('shows staff only the areas their role allows, and what needs a decision', async () => {
    mockFetch({ ...staff, 'GET /api/v1/admin/dashboard': { body: DASHBOARD } });
    renderRoute('/admin');
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();
    const nav = screen.getAllByRole('navigation', { name: 'Admin' })[0];
    if (!nav) throw new Error('admin navigation missing');
    expect(within(nav).getByRole('link', { name: 'Returns' })).toBeVisible();
    expect(within(nav).getByRole('link', { name: 'Reviews' })).toBeVisible();
    // Money and settings are admin-only (the backend enforces this too).
    expect(within(nav).queryByRole('link', { name: 'Gold rates' })).toBeNull();
    expect(within(nav).queryByRole('link', { name: 'Staff' })).toBeNull();
    expect(await screen.findByRole('link', { name: '1 open return' })).toHaveAttribute(
      'href',
      '/admin/returns',
    );
    expect(screen.getByRole('link', { name: '2 reviews to moderate' })).toBeVisible();
  });
});

describe('return requests', () => {
  it('offers only the actions the backend allows and requires a reason to reject', async () => {
    const user = userEvent.setup();
    const sent: unknown[] = [];
    mockFetch({
      ...staff,
      'GET /api/v1/admin/returns/r1': { body: RETURN },
      'POST /api/v1/admin/returns/r1/reject': async (request) => {
        sent.push(await request.json());
        return {
          status: 409,
          body: { error: { code: 'INVALID_RETURN_STATE', message: 'Already decided.' } },
        };
      },
      'POST /api/v1/admin/returns/r1/approve': async (request) => {
        sent.push(await request.json());
        return { body: { ...RETURN, status: 'approved', allowed_actions: ['receive', 'close'] } };
      },
    });
    renderRoute('/admin/returns/r1');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Return for ANV-261015-ABCDEF' }),
    ).toBeVisible();
    expect(screen.queryByRole('button', { name: /Mark as received/ })).toBeNull();

    // A server refusal is shown inside the dialog, which stays open.
    await user.click(screen.getByRole('button', { name: 'Reject…' }));
    const dialog = await screen.findByRole('dialog', { name: 'Reject this request' });
    expect(within(dialog).getByLabelText(/^Reason/)).toBeRequired();
    await user.type(within(dialog).getByLabelText(/^Reason/), 'Resized piece');
    await user.click(within(dialog).getByRole('button', { name: 'Reject request' }));
    expect(await within(dialog).findByText('Already decided.')).toBeVisible();
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    await user.click(screen.getByRole('button', { name: 'Approve…' }));
    const approve = await screen.findByRole('dialog', { name: 'Approve this request' });
    await user.click(within(approve).getByRole('button', { name: 'Approve' }));
    expect(await screen.findByRole('button', { name: /Mark as received/ })).toBeVisible();
    expect(sent).toEqual([{ note: 'Resized piece' }, { note: '' }]);
  });
});

describe('review moderation', () => {
  it('publishes a pending review', async () => {
    const user = userEvent.setup();
    let status: AdminReview['status'] = 'pending';
    mockFetch({
      ...staff,
      'GET /api/v1/admin/reviews': () => ({
        body: { items: [{ ...REVIEW, status }], page: 1, page_size: 25, total: 1, pages: 1 },
      }),
      'GET /api/v1/admin/dashboard': { body: DASHBOARD },
      'POST /api/v1/admin/reviews/v1/moderate': async (request) => {
        expect(await request.json()).toEqual({ decision: 'approve', note: '' });
        status = 'approved';
        return { body: { ...REVIEW, status } };
      },
    });
    renderRoute('/admin/reviews');
    expect(await screen.findByText('Lovely')).toBeVisible();
    expect(screen.getByRole('img', { name: '4 out of 5 stars' })).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Publish' }));
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Publish' })).toBeNull();
    });
    expect(screen.getByRole('button', { name: 'Unpublish…' })).toBeVisible();
  });
});
