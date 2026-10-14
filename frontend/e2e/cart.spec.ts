import { expect, test } from '@playwright/test';

/** Journey J1 (cart part): add to cart → change quantity → coupon → remove. Prices come from the API. */
test('add to cart, change quantity, apply a coupon and remove', async ({ page, isMobile }) => {
  await page.goto('/products/heritage-bridal-necklace');
  await expect(
    page.getByRole('heading', { level: 1, name: 'Heritage Bridal Necklace' }),
  ).toBeVisible();

  // One-of-a-kind piece: the quantity cannot go above 1.
  const panel = page.getByRole('group', { name: 'Quantity', exact: true });
  await expect(panel.getByRole('button', { name: 'Increase quantity' })).toBeDisabled();

  const addButton = isMobile
    ? page.getByRole('button', { name: 'Add Heritage Bridal Necklace to cart' })
    : page.getByRole('button', { name: 'Add to cart', exact: true });
  await addButton.click();
  await expect(page.getByRole('link', { name: 'Cart, 1 item' }).first()).toBeVisible();

  // Add a second piece with several in stock.
  await page.goto('/products/om-pendant');
  await (
    isMobile
      ? page.getByRole('button', { name: 'Add Om Pendant to cart' })
      : page.getByRole('button', { name: 'Add to cart', exact: true })
  ).click();
  await expect(page.getByRole('link', { name: 'Cart, 2 items' }).first()).toBeVisible();

  await page.getByRole('link', { name: 'Cart, 2 items' }).first().click();
  await expect(page.getByRole('heading', { level: 1, name: 'Your cart' })).toBeVisible();
  const [scrollWidth, width] = await page.evaluate(() => [
    document.documentElement.scrollWidth,
    window.innerWidth,
  ]);
  expect(scrollWidth, 'cart page must not scroll sideways').toBeLessThanOrEqual(width);
  const total = page.getByRole('table', { name: 'Price summary' }).getByRole('row').last();
  const before = await total.textContent();

  await page
    .getByRole('group', { name: 'Quantity of Om Pendant' })
    .getByRole('button', { name: 'Increase quantity' })
    .click();
  await expect(page.getByRole('link', { name: 'Cart, 3 items' }).first()).toBeVisible();
  await expect(total).not.toHaveText(before ?? '');

  await page.getByLabel('Coupon code').fill('welcome5');
  await page.getByRole('button', { name: 'Apply' }).click();
  await expect(page.getByText('You save ₹2,500.')).toBeVisible();
  await expect(page.getByRole('row', { name: /Coupon WELCOME5/ })).toBeVisible();

  await page.getByRole('button', { name: 'Remove Heritage Bridal Necklace from cart' }).click();
  await expect(page.getByRole('link', { name: 'Heritage Bridal Necklace' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Cart, 2 items' }).first()).toBeVisible();
});

test('expired coupon is explained', async ({ page, isMobile }) => {
  await page.goto('/products/om-pendant');
  await (
    isMobile
      ? page.getByRole('button', { name: 'Add Om Pendant to cart' })
      : page.getByRole('button', { name: 'Add to cart', exact: true })
  ).click();
  await expect(page.getByRole('link', { name: 'Cart, 1 item' }).first()).toBeVisible();
  await page.goto('/cart');
  await page.getByLabel('Coupon code').fill('EXPIRED10');
  await page.getByRole('button', { name: 'Apply' }).click();
  await expect(page.getByText('This coupon has expired.')).toBeVisible();
});
