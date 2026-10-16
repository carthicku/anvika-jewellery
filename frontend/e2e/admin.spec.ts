import { resolve } from 'node:path';

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

import { adjustStock, here, signInAsAdmin } from './helpers';

/*
 * Admin journeys: J8 (create a product → customers see it), J9 (inventory change), order
 * fulfilment with cancellation + simulated refund, and J10 (customers can't use the admin).
 * Everything created here is archived/cancelled again so repeated runs leave the sample store as
 * it was.
 */

test('staff land on the dashboard after a plain sign-in and see an Admin link', async ({
  page,
}) => {
  await signInAsAdmin(page, ''); // no ?next= : the normal /login page
  await expect(page).toHaveURL(/\/admin$/);
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'Admin dashboard' })).toBeVisible();
});

test('customers do not get an Admin link and land on their account', async ({ page }, testInfo) => {
  await page.goto('/register');
  await page.getByLabel(/^Full name/).fill('Plain Customer');
  await page
    .getByLabel(/^Email\*?$/)
    .fill(`plain-${testInfo.project.name}-${Date.now()}@example.com`);
  await page.getByLabel(/^Password/).fill('a long e2e passphrase');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/\/account$/);
  await expect(page.getByRole('link', { name: 'Admin dashboard' })).toHaveCount(0);
});

test('admin dashboard and navigation', async ({ page, isMobile }) => {
  await signInAsAdmin(page);
  await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();
  await expect(page.getByText('Net sales')).toBeVisible();
  const [dashWidth, viewport] = await page.evaluate(() => [
    document.documentElement.scrollWidth,
    window.innerWidth,
  ]);
  expect(dashWidth, 'dashboard must not scroll sideways').toBeLessThanOrEqual(viewport);
  if (isMobile) {
    await page.getByRole('button', { name: 'Open admin menu' }).click();
  }
  const nav = page.getByRole('navigation', { name: 'Admin' }).last();
  for (const label of ['Orders', 'Products', 'Inventory', 'Gold rates', 'Staff', 'Audit log']) {
    await expect(nav.getByRole('link', { name: label })).toBeVisible();
  }
  await nav.getByRole('link', { name: 'Gold rates' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Gold rates' })).toBeVisible();
  const [scrollWidth, width] = await page.evaluate(() => [
    document.documentElement.scrollWidth,
    window.innerWidth,
  ]);
  expect(scrollWidth, 'admin must not scroll sideways').toBeLessThanOrEqual(width);
});

test('create a product with a photo, publish it, adjust stock, then archive it', async ({
  page,
}, testInfo) => {
  const stamp = `${testInfo.project.name === 'mobile-chrome' ? 'M' : 'D'}${Date.now().toString(36).toUpperCase()}`;
  const name = `E2E Lotus Ring ${stamp}`;
  await signInAsAdmin(page, '/admin/products/new');

  await page.getByLabel(/^Name/).first().fill(name);
  await page.getByLabel(/^Category/).selectOption({ label: 'Rings' });
  await page.getByLabel('Making charge value').fill('12');
  await page.getByLabel(/^SKU/).fill(`E2E-${stamp}`);
  await page.getByLabel('Label', { exact: false }).first().fill('Size 12');
  await page.getByLabel('Net gold weight (g)').fill('4.000');
  await page.getByLabel('Initial stock').fill('2');

  await page.getByRole('button', { name: 'Calculate prices' }).click();
  await expect(page.getByRole('table', { name: 'Price of Size 12' })).toBeVisible();

  await page.getByRole('button', { name: 'Create draft' }).click();
  await expect(page.getByRole('heading', { level: 1, name })).toBeVisible();
  await expect(page).toHaveURL(/\/admin\/products\/[0-9a-f-]{36}$/);
  const productUrl = page.url();

  // Photo upload (re-encoded to WebP by the server).
  await page.getByLabel('Description for screen readers').fill('Test photo of a ring outline');
  await page.locator('input[type=file]').setInputFiles(resolve(here, 'fixtures/test-photo.png'));
  await expect(page.getByText('Photo uploaded.')).toBeVisible();
  await expect(page.getByRole('img', { name: 'Test photo of a ring outline' })).toBeVisible();

  // Publish.
  await page.getByLabel('Status', { exact: false }).last().selectOption('active');
  await page.getByRole('button', { name: 'Save product' }).click();
  await expect(page.getByText('Product saved.')).toBeVisible();
  const slug = (await page.getByLabel('Web address').inputValue()).trim();

  // Customers can see it, priced by the backend.
  await page.goto(`/products/${slug}`);
  await expect(page.getByRole('heading', { level: 1, name })).toBeVisible();
  await expect(page.getByText(/₹[\d,]+/).first()).toBeVisible();

  // J9: stock adjustment is recorded.
  await page.goto(`/admin/inventory`);
  await page.getByLabel('Search', { exact: false }).fill(`E2E-${stamp}`);
  await page.getByRole('button', { name: 'Search' }).click();
  const row = page.getByRole('row', { name: new RegExp(`E2E-${stamp}`) });
  await expect(row.getByRole('cell').nth(1)).toHaveText('2');
  await row.getByRole('button', { name: 'Adjust…' }).click();
  await page.getByLabel(/^Change/).fill('3');
  await page.getByLabel(/^Reason/).fill('E2E delivery from workshop');
  await page.getByRole('button', { name: 'Save adjustment' }).click();
  await expect(page.getByText('Stock updated.')).toBeVisible();
  await expect(row.getByRole('cell').nth(1)).toHaveText('5');

  // Clean up: archive (products are never deleted).
  await page.goto(productUrl);
  await page.getByLabel('Status', { exact: false }).last().selectOption('archived');
  await page.getByRole('button', { name: 'Save product' }).click();
  await expect(page.getByText('Product saved.')).toBeVisible();
  await page.goto(`/products/${slug}`);
  await expect(page.getByRole('heading', { level: 1, name })).toHaveCount(0);
});

/** Buy the Om Pendant with the simulator; a guest when `email` is given. Returns the reference. */
async function buyOmPendant(page: Page, isMobile: boolean, email: string | null) {
  await page.goto('/products/om-pendant');
  await (
    isMobile
      ? page.getByRole('button', { name: 'Add Om Pendant to cart' })
      : page.getByRole('button', { name: 'Add to cart', exact: true })
  ).click();
  await expect(page.getByRole('link', { name: /^Cart, [1-9]/ }).first()).toBeVisible();
  await page.goto('/checkout');
  if (email) await page.getByLabel(/^Email\*?$/).fill(email);
  await page.getByLabel(/^Full name/).fill('Asha Rao');
  await page.getByLabel(/^Mobile number/).fill('9876543210');
  await page.getByLabel(/^House/).fill('12 MG Road');
  await page.getByLabel(/^PIN code/).fill('560001');
  await page.getByLabel(/^City/).fill('Bengaluru');
  await page.getByLabel(/^State/).selectOption('Karnataka');
  await expect(page.getByRole('radio', { name: /Standard delivery/ })).toBeChecked();
  await page.getByRole('checkbox', { name: /I agree to the terms/ }).check();
  await page.getByRole('button', { name: /^Place order and pay ₹/ }).click();
  await page
    .getByRole('dialog', { name: 'Simulated payment' })
    .getByRole('button', { name: 'Pay (simulated)' })
    .click();
  await expect(page).toHaveURL(/\/order-confirmation\/ANV-/);
  return page.url().split('/').pop() ?? '';
}

/** Staff take a paid order through preparing → shipped → delivered. */
async function deliver(admin: Page, reference: string) {
  await admin.goto(`/admin/orders/${reference}`);
  await admin.getByRole('button', { name: 'Start preparing' }).click();
  await expect(admin.getByText('Marked as being prepared.')).toBeVisible();
  await admin.getByRole('button', { name: 'Ship…' }).click();
  const ship = admin.getByRole('dialog', { name: 'Ship this order' });
  await ship.getByLabel(/^Courier/).fill('Sample Courier');
  await ship.getByLabel(/^Tracking number/).fill('E2E123456');
  await ship.getByRole('button', { name: 'Mark as shipped' }).click();
  await expect(admin.getByText('Marked as shipped.')).toBeVisible();
  await admin.getByRole('button', { name: 'Mark delivered' }).click();
  await expect(admin.getByRole('button', { name: 'Mark delivered' })).toHaveCount(0);
}

test('prepare, cancel and refund an order', async ({ page, isMobile }, testInfo) => {
  // A guest buys a piece with the simulator.
  const reference = await buyOmPendant(
    page,
    isMobile,
    `admin-flow-${testInfo.project.name}-${Date.now()}@example.com`,
  );

  // Staff side (fresh browser context: the admin signs in).
  await page.context().clearCookies();
  await signInAsAdmin(page, `/admin/orders/${reference}`);
  await expect(page.getByRole('heading', { level: 1, name: `Order ${reference}` })).toBeVisible();
  await page.getByRole('button', { name: 'Start preparing' }).click();
  await expect(page.getByText('Marked as being prepared.')).toBeVisible();

  await page.getByRole('button', { name: 'Cancel order…' }).click();
  await page.getByLabel(/^Reason/).fill('E2E: customer changed their mind');
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel order' }).click();
  await expect(page.getByText('Order cancelled.')).toBeVisible();

  await page.getByRole('button', { name: /^Send refund ₹/ }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Send refund' }).click();
  await expect(page.getByText('Refund sent.')).toBeVisible();
  await expect(page.getByText(/Refunded/).first()).toBeVisible();
});

test('return a delivered piece: request, approval, restock and refund', async ({
  page,
  browser,
  isMobile,
}, testInfo) => {
  const reference = await buyOmPendant(
    page,
    isMobile,
    `return-flow-${testInfo.project.name}-${Date.now()}@example.com`,
  );
  const staffContext = await browser.newContext();
  const admin = await staffContext.newPage();
  await signInAsAdmin(admin, `/admin/orders/${reference}`);
  await deliver(admin, reference);

  // The customer (still on their private order link) asks for a return.
  await page.reload();
  await page.getByRole('button', { name: 'Request a return or exchange' }).click();
  const ask = page.getByRole('dialog', { name: 'Return or exchange' });
  await ask.getByRole('combobox').first().selectOption('1');
  await ask.getByLabel(/^Reason/).fill('E2E: the chain is shorter than I expected');
  await ask.getByRole('button', { name: 'Send request' }).click();
  await expect(page.getByText('Requested — waiting for our reply')).toBeVisible();

  // Staff approve, receive (back into stock) and refund.
  await admin.goto('/admin/returns');
  await admin.getByRole('link', { name: `Return · ${reference}` }).click();
  await admin.getByRole('button', { name: 'Approve…' }).click();
  await admin
    .getByRole('dialog', { name: 'Approve this request' })
    .getByRole('button', { name: 'Approve' })
    .click();
  await expect(admin.getByText('Request approved.')).toBeVisible();
  await admin.getByRole('button', { name: 'Mark as received…' }).click();
  const receive = admin.getByRole('dialog', { name: 'Items received' });
  await receive.getByRole('checkbox').first().check();
  await receive.getByRole('button', { name: 'Save' }).click();
  await expect(admin.getByText('Restocked')).toBeVisible();
  await admin.getByRole('button', { name: /^Refund ₹/ }).click();
  await admin
    .getByRole('dialog', { name: 'Refund the returned pieces' })
    .getByRole('button', { name: 'Request refund' })
    .click();
  await expect(admin.getByText('Refund requested.')).toBeVisible();
  await admin.getByRole('link', { name: 'order page' }).click();
  await admin.getByRole('button', { name: /^Send refund ₹/ }).click();
  await admin.getByRole('dialog').getByRole('button', { name: 'Send refund' }).click();
  await expect(admin.getByText('Refund sent.')).toBeVisible();
  await staffContext.close();

  await page.reload();
  await expect(page.getByText('Refund issued', { exact: true })).toBeVisible();
  await expect(page.getByText('Order returned')).toBeVisible();
});

test('a delivered buyer reviews a piece; it shows only after staff publish it', async ({
  page,
  browser,
  isMobile,
}, testInfo) => {
  const title = `E2E review ${testInfo.project.name} ${Date.now().toString(36)}`;
  await page.goto('/register');
  await page.getByLabel(/^Full name/).fill('Meera Iyer');
  await page
    .getByLabel(/^Email\*?$/)
    .fill(`reviewer-${testInfo.project.name}-${Date.now()}@example.com`);
  await page.getByLabel(/^Password/).fill('a long e2e passphrase');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/\/account$/);
  const reference = await buyOmPendant(page, isMobile, null);

  const staffContext = await browser.newContext();
  const admin = await staffContext.newPage();
  await signInAsAdmin(admin, `/admin/orders/${reference}`);
  await deliver(admin, reference);

  await page.goto('/products/om-pendant');
  const reviews = page.getByRole('region', { name: 'Reviews' });
  await reviews.getByRole('radio', { name: '4 stars' }).check({ force: true });
  await reviews.getByLabel(/^Title/).fill(title);
  await reviews.getByLabel(/^Your review/).fill('Delicate and well finished; arrived safely.');
  await reviews.getByRole('button', { name: 'Submit review' }).click();
  await expect(page.getByText('Waiting for approval')).toBeVisible();
  await expect(page.getByText(title)).toHaveCount(0);

  await admin.goto('/admin/reviews');
  const card = admin.getByRole('listitem').filter({ hasText: title });
  await card.getByRole('button', { name: 'Publish' }).click();
  await expect(admin.getByText('Review published.')).toBeVisible();
  await expect(card).toHaveCount(0); // no longer waiting for approval

  await page.reload();
  const shown = page.getByRole('listitem').filter({ hasText: title });
  await expect(shown).toBeVisible();
  await expect(shown.getByText('Meera I. · Verified purchase', { exact: false })).toBeVisible();

  // Clean up so the sample store doesn't collect test reviews.
  await admin.getByRole('combobox', { name: 'Show' }).selectOption('approved');
  const published = admin.getByRole('listitem').filter({ hasText: title });
  await published.getByRole('button', { name: 'Unpublish…' }).click();
  await admin.getByRole('dialog').getByRole('button', { name: 'Reject' }).click();
  await expect(admin.getByText('Review rejected.')).toBeVisible();

  // The test sale stays delivered; put the piece back so repeated runs don't use up sample stock.
  await adjustStock(admin, 'ANV-PD-001', 1, 'E2E: return sample stock used by the review test');
  await staffContext.close();
});

test('admin screens have no serious accessibility violations', async ({ page }) => {
  await signInAsAdmin(page);
  for (const path of [
    '/admin',
    '/admin/products/new',
    '/admin/orders',
    '/admin/gold-rates',
    '/admin/returns',
    '/admin/reviews',
  ]) {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze();
    const serious = results.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical',
    );
    expect(
      serious.map(
        (v) => `${path} ${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(' ')).join(', ')})`,
      ),
    ).toEqual([]);
  }
});

test('customers cannot use the admin', async ({ page }, testInfo) => {
  await page.goto('/register');
  await page.getByLabel(/^Full name/).fill('Curious Customer');
  await page
    .getByLabel(/^Email\*?$/)
    .fill(`curious-${testInfo.project.name}-${Date.now()}@example.com`);
  await page.getByLabel(/^Password/).fill('a long e2e passphrase');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/\/account$/);
  await page.goto('/admin');
  await expect(page.getByRole('heading', { name: 'This area is for store staff' })).toBeVisible();
  await page.goto('/admin/orders');
  await expect(page.getByRole('heading', { name: 'This area is for store staff' })).toBeVisible();
});
