import { expect, test } from '@playwright/test';

/** Journey J2: register → account → add / edit / delete an address → sign out → sign in. */
test('register, manage addresses, sign out and sign back in', async ({ page }, testInfo) => {
  const email = `e2e-${testInfo.project.name}-${Date.now()}@example.com`;
  const password = 'a long e2e passphrase';

  await page.goto('/register');
  await page.getByLabel(/^Full name/).fill('Asha Rao');
  await page.getByLabel(/^Email\*?$/).fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page).toHaveURL(/\/account$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Hello, Asha' })).toBeVisible();
  await expect(page.getByText('Please confirm your email address')).toBeVisible();

  // Add an address.
  await page
    .getByRole('navigation', { name: 'Account' })
    .getByRole('link', { name: 'Addresses' })
    .click();
  await page.getByRole('button', { name: 'Add your first address' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel(/^Full name/).fill('Asha Rao');
  await dialog.getByLabel(/^Mobile number/).fill('9876543210');
  await dialog.getByLabel(/^House/).fill('12 MG Road');
  await dialog.getByLabel(/^PIN code/).fill('560001');
  await dialog.getByLabel(/^City/).fill('Bengaluru');
  await dialog.getByLabel(/^State/).selectOption('Karnataka');
  await dialog.getByRole('button', { name: 'Save address' }).click();
  await expect(page.getByText('12 MG Road')).toBeVisible();
  await expect(page.getByText('Default delivery')).toBeVisible();

  // Edit it.
  await page.getByRole('button', { name: 'Edit' }).click();
  await page
    .getByRole('dialog')
    .getByLabel(/^Landmark/)
    .fill('Near the metro');
  await page.getByRole('dialog').getByRole('button', { name: 'Save address' }).click();
  await expect(page.getByText('Near Near the metro')).toBeVisible();

  // Delete it (with confirmation).
  await page.getByRole('button', { name: /Delete address 12 MG Road/ }).click();
  await page.getByRole('button', { name: 'Delete address', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'No saved addresses' })).toBeVisible();

  // Sign out, then back in.
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page).toHaveURL('/');
  await page.goto('/account');
  await expect(page).toHaveURL(/\/login\?next=%2Faccount/);
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/account$/);
});

test('wrong password is refused with a clear message', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('nobody@example.com');
  await page.getByLabel('Password').fill('not the password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByText('The email or password is incorrect.')).toBeVisible();
});
