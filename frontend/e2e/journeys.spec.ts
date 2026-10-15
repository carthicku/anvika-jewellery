import { expect, test } from '@playwright/test';

import { addToCart, adjustStock, adminPage, setGoldRate } from './helpers';

/*
 * Journeys J6/J9 (stock runs out), J7 (gold rate changes while a piece is in the cart) and J12
 * (keyboard and responsive). Each test puts the sample data back as it found it (stock adjustments
 * and rates are audited, append-only changes — nothing is deleted).
 */

test('a piece that sells out is blocked in the cart and at checkout (J6, J9)', async ({
  page,
  browser,
  isMobile,
}) => {
  const sku = 'ANV-ER-003';
  await addToCart(page, 'crescent-hoops', 'Crescent Hoops', isMobile);

  const staff = await adminPage(browser, '/admin/inventory');
  // Read what is on hand now (from the API, so a half-rendered table can't mislead the test),
  // then take all of it off the shelf.
  const levels = (await (
    await staff.page.request.get(`/api/v1/admin/inventory?q=${sku}`)
  ).json()) as { items: { sku: string; on_hand: number; reserved: number }[] };
  const level = levels.items.find((i) => i.sku === sku);
  expect(level?.reserved, 'no other order may hold this piece').toBe(0);
  const onHand = level?.on_hand ?? 0;
  expect(onHand).toBeGreaterThan(0);
  try {
    await adjustStock(staff.page, sku, -onHand, 'E2E: sold out elsewhere (J9)');

    await page.goto('/products/crescent-hoops');
    await expect(page.getByText('This size is currently out of stock')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add to cart', exact: true })).toHaveCount(0);

    await page.goto('/cart');
    await expect(page.getByText('Please review your cart')).toBeVisible();
    await expect(page.getByText('Out of stock', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Proceed to checkout' })).toHaveCount(0);
    await page.goto('/checkout');
    await expect(page.getByRole('button', { name: /^Place order and pay/ })).toHaveCount(0);
  } finally {
    await adjustStock(staff.page, sku, onHand, 'E2E: restore sample stock (J9)');
    await staff.close();
  }
  await page.goto('/cart');
  await expect(page.getByRole('link', { name: 'Proceed to checkout' }).first()).toBeVisible();
});

test('a higher gold rate must be accepted before checkout (J7)', async ({
  page,
  browser,
  isMobile,
}) => {
  await addToCart(page, 'box-chain', 'Box Chain', isMobile);
  await page.goto('/cart');
  await expect(page.getByRole('link', { name: 'Proceed to checkout' }).first()).toBeVisible();

  const staff = await adminPage(browser, '/admin/gold-rates');
  const rates = (await (await staff.page.request.get('/api/v1/admin/gold-rates')).json()) as {
    current: { purity: string; rate_per_gram: string | null }[];
  };
  const current = rates.current.find((r) => r.purity === '18K')?.rate_per_gram ?? '0';
  expect(Number(current)).toBeGreaterThan(0);
  const higher = (Number(current) + 50).toFixed(2);
  try {
    await setGoldRate(staff.page, '18K', higher, 'E2E: temporary test rate (J7)');

    await page.reload();
    await expect(page.getByText('Price increased')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Proceed to checkout' })).toHaveCount(0);
    await page.getByRole('button', { name: 'Accept updated prices' }).click();
    await expect(page.getByText('Price increased')).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Proceed to checkout' }).first()).toBeVisible();
  } finally {
    await setGoldRate(staff.page, '18K', current, 'E2E: restore the previous sample rate (J7)');
    await staff.close();
  }
  // Back at the old rate the price drops, which is applied with a notice (no acceptance needed).
  await page.reload();
  await expect(page.getByRole('link', { name: 'Proceed to checkout' }).first()).toBeVisible();
});

test('keyboard only: product → add to cart → cart → checkout (J12)', async ({ page, isMobile }) => {
  test.skip(isMobile, 'Keyboard flow is checked on desktop');
  await page.goto('/products/box-chain');
  await expect(page.getByRole('heading', { level: 1, name: 'Box Chain' })).toBeVisible();
  const add = page.getByRole('button', { name: 'Add to cart', exact: true });
  // Tab until the button has focus (no mouse), then press Enter.
  for (let i = 0; i < 60 && !(await add.evaluate((el) => el === document.activeElement)); i++) {
    await page.keyboard.press('Tab');
  }
  await expect(add).toBeFocused();
  await page.keyboard.press('Enter');
  const cartLink = page.getByRole('link', { name: /^Cart, [1-9]/ }).first();
  await expect(cartLink).toBeVisible();
  await cartLink.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/cart$/);
  const proceed = page.getByRole('link', { name: 'Proceed to checkout' });
  await proceed.focus();
  await expect(proceed).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/checkout$/);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
});

test('layouts work at 375, 768 and 1280 px without sideways scrolling (J12)', async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, 'Viewport sizes are set explicitly on the desktop project');
  for (const width of [375, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ['/', '/collections/rings', '/products/box-chain', '/cart', '/checkout']) {
      await page.goto(path);
      await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
      const [scrollWidth, innerWidth] = await page.evaluate(() => [
        document.documentElement.scrollWidth,
        window.innerWidth,
      ]);
      expect(scrollWidth, `${path} at ${String(width)} px`).toBeLessThanOrEqual(innerWidth);
    }
  }
});
