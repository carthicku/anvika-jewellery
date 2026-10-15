import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

/*
 * Admin journeys: J8 (create a product → customers see it), J9 (inventory change), order
 * fulfilment with cancellation + simulated refund, and J10 (customers can't use the admin).
 * Everything created here is archived/cancelled again so repeated runs leave the sample store as
 * it was. The admin account and its random password come from e2e/global-setup.ts.
 */
const here = dirname(fileURLToPath(import.meta.url));
const credentials = (): { email: string; password: string } =>
  JSON.parse(readFileSync(resolve(here, '.auth/admin.json'), 'utf8')) as {
    email: string;
    password: string;
  };

async function signInAsAdmin(page: Page, next = '/admin') {
  const { email, password } = credentials();
  await page.goto(`/login?next=${encodeURIComponent(next)}`);
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(new RegExp(`${next}$`));
}

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

test('prepare, cancel and refund an order', async ({ page, isMobile }, testInfo) => {
  // A guest buys a piece with the simulator.
  await page.goto('/products/om-pendant');
  await (
    isMobile
      ? page.getByRole('button', { name: 'Add Om Pendant to cart' })
      : page.getByRole('button', { name: 'Add to cart', exact: true })
  ).click();
  await expect(page.getByRole('link', { name: /^Cart, [1-9]/ }).first()).toBeVisible();
  await page.goto('/checkout');
  await page
    .getByLabel(/^Email\*?$/)
    .fill(`admin-flow-${testInfo.project.name}-${Date.now()}@example.com`);
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
  const reference = page.url().split('/').pop() ?? '';

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

test('admin screens have no serious accessibility violations', async ({ page }) => {
  await signInAsAdmin(page);
  for (const path of ['/admin', '/admin/products/new', '/admin/orders', '/admin/gold-rates']) {
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
