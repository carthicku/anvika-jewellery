import { expect, test } from '@playwright/test';

test('home page loads catalogue data from the API', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Gold jewellery');
  await expect(page.getByRole('heading', { name: 'New arrivals' })).toBeVisible();
  await expect(page.locator('a[href^="/products/"]').first()).toBeVisible();
});

test('unknown routes show the 404 page', async ({ page }) => {
  await page.goto('/no-such-page');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/couldn.t find that page/i);
  await page.getByRole('link', { name: 'Return to the homepage' }).click();
  await expect(page).toHaveURL('/');
});

test('every storefront route renders without errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  const routes = [
    '/collections',
    '/collections/rings',
    '/collections/bridal-heirlooms',
    '/search?q=ring',
    '/products/everyday-gold-band',
    '/wishlist',
    '/contact',
    '/about',
    '/faq',
    '/jewellery-care',
    '/gold-buying-guide',
    '/shipping-policy',
    '/returns-and-exchanges',
    '/privacy-policy',
    '/terms-and-conditions',
    '/refund-policy',
  ];
  for (const route of routes) {
    await page.goto(route);
    await expect(page.getByRole('heading', { level: 1 }), route).toBeVisible();
  }
  expect(errors).toEqual([]);
});

test('no page scrolls sideways on a phone', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Checked on the mobile project');
  for (const route of [
    '/',
    '/collections',
    '/collections/rings',
    '/products/everyday-gold-band',
    '/search?q=ring',
    '/wishlist',
    '/contact',
    '/gold-buying-guide',
    '/login',
    '/register',
    '/cart',
  ]) {
    await page.goto(route);
    await expect(page.getByRole('heading', { level: 1 }), route).toBeVisible();
    const [scrollWidth, width] = await page.evaluate(() => [
      document.documentElement.scrollWidth,
      window.innerWidth,
    ]);
    expect(scrollWidth, `${route} is wider than the screen`).toBeLessThanOrEqual(width);
  }
});
