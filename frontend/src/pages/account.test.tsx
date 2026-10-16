import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { User } from '@/api/queries/account';
import { safeNext } from '@/lib/forms';
import { detail, page } from '@/test/fixtures';
import { mockFetch, renderRoute, requestedUrls } from '@/test/utils';

const USER: User = {
  id: 'u1',
  email: 'asha@example.com',
  full_name: 'Asha Rao',
  phone: null,
  role: 'customer',
  email_verified: true,
  permissions: [],
};

const signedIn = { 'GET /api/v1/auth/me': { body: { user: USER } } };

describe('safeNext (open-redirect protection)', () => {
  it.each([
    ['/account/addresses', '/account/addresses'],
    ['//evil.example', '/account'],
    ['https://evil.example', '/account'],
    ['/\\evil.example', '/account'],
    [null, '/account'],
  ])('%s → %s', (input, expected) => {
    expect(safeNext(input)).toBe(expected);
  });
});

describe('account access', () => {
  it('sends guests to sign-in and remembers where they were going', async () => {
    mockFetch({});
    const { router } = renderRoute('/account/addresses');
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/login');
    });
    expect(router.state.location.search).toBe('?next=%2Faccount%2Faddresses');
  });
});

describe('sign in', () => {
  it('shows a clear message for wrong credentials', async () => {
    const user = userEvent.setup();
    mockFetch({
      'POST /api/v1/auth/login': {
        status: 401,
        body: {
          error: { code: 'INVALID_CREDENTIALS', message: 'The email or password is incorrect.' },
        },
      },
    });
    renderRoute('/login');
    await user.type(await screen.findByLabelText('Email'), 'asha@example.com');
    await user.type(screen.getByLabelText('Password'), 'wrong password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByText('The email or password is incorrect.')).toBeInTheDocument();
  });

  it('signs in, merges the guest wishlist and continues to the requested page', async () => {
    const user = userEvent.setup();
    window.localStorage.setItem('anvika:wishlist:v1', JSON.stringify(['om-pendant']));
    let mergedBody: unknown = null;
    mockFetch({
      'POST /api/v1/auth/login': { body: { user: USER } },
      'POST /api/v1/wishlist/merge': async (request) => {
        mergedBody = await request.json();
        return { body: { ok: true, message: '1 added' } };
      },
      'GET /api/v1/wishlist/slugs': { body: ['om-pendant'] },
      'GET /api/v1/me/addresses': { body: [] },
    });
    const { router } = renderRoute('/login?next=/account/addresses');
    await user.type(await screen.findByLabelText('Email'), 'asha@example.com');
    await user.type(screen.getByLabelText('Password'), 'correct horse battery');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/account/addresses');
    });
    expect(mergedBody).toEqual({ slugs: ['om-pendant'] });
    expect(window.localStorage.getItem('anvika:wishlist:v1')).toBe('[]');
  });

  it.each([
    ['staff', ['dashboard:view', 'orders:write'], '/admin'],
    ['customer', [], '/account'],
  ])('sends a %s to %s after a plain sign-in', async (_kind, permissions, expected) => {
    const user = userEvent.setup();
    mockFetch({
      'POST /api/v1/auth/login': {
        body: { user: { ...USER, role: permissions.length ? 'staff' : 'customer', permissions } },
      },
      'POST /api/v1/wishlist/merge': { body: { ok: true, message: '' } },
      'GET /api/v1/wishlist/slugs': { body: [] },
      'GET /api/v1/me/addresses': { body: [] },
      'GET /api/v1/admin/dashboard': {
        status: 403,
        body: { error: { code: 'FORBIDDEN', message: 'x' } },
      },
    });
    const { router } = renderRoute('/login');
    await user.type(await screen.findByLabelText('Email'), 'asha@example.com');
    await user.type(screen.getByLabelText('Password'), 'correct horse battery');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(expected);
    });
  });
});

describe('registration', () => {
  it('validates the password before contacting the server', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetch({});
    renderRoute('/register');
    await user.type(await screen.findByLabelText(/Full name/), 'Asha Rao');
    await user.type(screen.getByLabelText(/^Email\*?$/), 'asha@example.com');
    await user.type(screen.getByLabelText(/Password/), '1234567890');
    await user.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByText("Don't use only numbers.")).toBeInTheDocument();
    expect(requestedUrls(fetchMock).some((u) => u.pathname === '/api/v1/auth/register')).toBe(
      false,
    );
  });

  it('offers a password reset when the email is already registered', async () => {
    const user = userEvent.setup();
    mockFetch({
      'POST /api/v1/auth/register': {
        status: 409,
        body: {
          error: { code: 'EMAIL_IN_USE', message: 'An account with this email already exists.' },
        },
      },
    });
    renderRoute('/register');
    await user.type(await screen.findByLabelText(/Full name/), 'Asha Rao');
    await user.type(screen.getByLabelText(/^Email\*?$/), 'asha@example.com');
    await user.type(screen.getByLabelText(/Password/), 'a good long passphrase');
    await user.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByRole('link', { name: 'Reset your password' })).toHaveAttribute(
      'href',
      '/forgot-password',
    );
  });
});

describe('addresses', () => {
  it('validates and saves a new address', async () => {
    const user = userEvent.setup();
    let saved: Record<string, unknown> | null = null;
    mockFetch({
      ...signedIn,
      'GET /api/v1/me/addresses': { body: [] },
      'POST /api/v1/me/addresses': async (request) => {
        saved = (await request.json()) as Record<string, unknown>;
        return { status: 201, body: { id: 'a1', country: 'IN', ...saved } };
      },
    });
    renderRoute('/account/addresses');
    await user.click(await screen.findByRole('button', { name: 'Add your first address' }));
    await user.type(screen.getByLabelText(/Full name/), 'Asha Rao');
    await user.type(screen.getByLabelText(/Mobile number/), '98765 43210');
    await user.type(screen.getByLabelText(/House/), '12 MG Road');
    await user.type(screen.getByLabelText(/PIN code/), '012345');
    await user.type(screen.getByLabelText(/City/), 'Bengaluru');
    await user.selectOptions(screen.getByLabelText(/State/), 'Karnataka');
    await user.click(screen.getByRole('button', { name: 'Save address' }));
    expect(await screen.findByText('Enter a valid 6-digit PIN code.')).toBeInTheDocument();
    expect(saved).toBeNull();

    await user.clear(screen.getByLabelText(/PIN code/));
    await user.type(screen.getByLabelText(/PIN code/), '560001');
    await user.click(screen.getByRole('button', { name: 'Save address' }));
    await waitFor(() => {
      expect(saved).toMatchObject({
        full_name: 'Asha Rao',
        pincode: '560001',
        state: 'Karnataka',
        line2: null,
        landmark: null,
      });
    });
  });
});

describe('signed-in wishlist', () => {
  it('saves to the account instead of the browser', async () => {
    const user = userEvent.setup();
    const serverWishlist: string[] = [];
    const fetchMock = mockFetch({
      ...signedIn,
      'GET /api/v1/wishlist/slugs': () => ({ body: [...serverWishlist] }),
      'PUT /api/v1/wishlist/everyday-gold-band': () => {
        serverWishlist.push('everyday-gold-band');
        return { body: { ok: true } };
      },
      'GET /api/v1/products/everyday-gold-band': { body: detail },
      'GET /api/v1/products/everyday-gold-band/related': { body: [] },
      'GET /api/v1/products': { body: page([]) },
    });
    renderRoute('/products/everyday-gold-band');
    await user.click(await screen.findByRole('button', { name: 'Save to wishlist' }));
    expect(await screen.findByRole('button', { name: 'Saved to wishlist' })).toBeInTheDocument();
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input]) =>
            input instanceof Request &&
            input.method === 'PUT' &&
            input.url.endsWith('/wishlist/everyday-gold-band'),
        ),
      ).toBe(true);
    });
    expect(window.localStorage.getItem('anvika:wishlist:v1')).toBeNull();
  });
});
