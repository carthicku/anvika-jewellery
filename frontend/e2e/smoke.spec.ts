import { expect, test } from '@playwright/test';

test('home page loads and talks to the API', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.getByRole('status')).toHaveText(/API connected/);
});

test('unknown routes show the 404 page', async ({ page }) => {
  await page.goto('/no-such-page');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/couldn.t find that page/i);
  await page.getByRole('link', { name: 'Return to the homepage' }).click();
  await expect(page).toHaveURL('/');
});
