import { expect, test } from '@playwright/test';

/** Journey J1 (browse part): category → filter → product → size → delivery check → wishlist. */
test('browse, filter, choose a size, check delivery and save to wishlist', async ({
  page,
  isMobile,
}) => {
  await page.goto('/collections/rings');
  await expect(page.getByRole('heading', { level: 1, name: 'Rings' })).toBeVisible();
  await expect(page.getByText('4 pieces')).toBeVisible();

  // Filter by purity (desktop sidebar or mobile drawer).
  if (isMobile) await page.getByRole('button', { name: /^Filters/ }).click();
  await page.getByRole('checkbox', { name: /22K/ }).first().click();
  await expect(page).toHaveURL(/purity=22K/);
  if (isMobile) await page.getByRole('button', { name: /^Show/ }).click();
  await expect(page.getByText('2 pieces')).toBeVisible();

  await page.getByRole('link', { name: 'Everyday Gold Band' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Everyday Gold Band' })).toBeVisible();
  const price = page.locator('[aria-live="polite"]').filter({ hasText: '₹' }).first();
  const before = await price.textContent();
  await page.locator('label', { hasText: /^16$/ }).click();
  await expect(price).not.toHaveText(before ?? '');

  await page.getByLabel('Delivery PIN code').fill('560001');
  await page.getByRole('button', { name: 'Check' }).click();
  await expect(page.getByText('Standard delivery', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Save to wishlist' }).click();
  await expect(page.getByRole('button', { name: 'Saved to wishlist' })).toBeVisible();
  await page
    .getByRole('link', { name: /Wishlist, 1 saved/ })
    .first()
    .click();
  await expect(page.getByRole('heading', { level: 1, name: 'Your wishlist' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Everyday Gold Band' })).toBeVisible();
});

test('search from the header shows suggestions and results', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Search' }).first().click();
  await page.getByLabel('Search jewellery').fill('jhumka');
  await expect(page.getByRole('link', { name: /Meenakshi Jhumkas/ })).toBeVisible();
  await page.getByLabel('Search jewellery').press('Enter');
  await expect(page).toHaveURL(/\/search\?q=jhumka/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('jhumka');
});
