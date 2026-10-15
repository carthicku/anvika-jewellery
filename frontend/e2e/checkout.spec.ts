import { expect, test, type Page } from '@playwright/test';

/*
 * Journeys J3 (guest checkout), J4 (payment failure and retry), J11 (cancel an eligible order)
 * and signed-in checkout → order history. Payments use the development simulator — no money
 * moves. Every paid order is cancelled at the end (which puts the piece back in stock), so
 * repeated runs don't use up the sample catalogue.
 */

async function addOmPendant(page: Page, isMobile: boolean) {
  await page.goto('/products/om-pendant');
  await (
    isMobile
      ? page.getByRole('button', { name: 'Add Om Pendant to cart' })
      : page.getByRole('button', { name: 'Add to cart', exact: true })
  ).click();
  await expect(page.getByRole('link', { name: /^Cart, [1-9]/ }).first()).toBeVisible();
}

async function fillAddress(page: Page) {
  await page.getByLabel(/^Full name/).fill('Asha Rao');
  await page.getByLabel(/^Mobile number/).fill('9876543210');
  await page.getByLabel(/^House/).fill('12 MG Road');
  await page.getByLabel(/^PIN code/).fill('560001');
  await page.getByLabel(/^City/).fill('Bengaluru');
  await page.getByLabel(/^State/).selectOption('Karnataka');
}

async function placeOrder(page: Page) {
  await expect(page.getByRole('radio', { name: /Standard delivery/ })).toBeChecked();
  await page.getByRole('checkbox', { name: /I agree to the terms/ }).check();
  await page.getByRole('button', { name: /^Place order and pay ₹/ }).click();
}

async function cancelOrder(page: Page) {
  await page.getByRole('button', { name: 'Cancel order' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel order' }).click();
  await expect(
    page.getByRole('heading', { level: 1, name: 'This order was cancelled' }),
  ).toBeVisible();
}

test('guest checks out, pays (simulated) and cancels', async ({ page, isMobile }, testInfo) => {
  await addOmPendant(page, isMobile);
  await page.goto('/cart');
  await page.getByRole('link', { name: 'Proceed to checkout' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Checkout' })).toBeVisible();

  // Until a delivery PIN code is entered there is no final total, so ordering is disabled.
  await expect(page.getByRole('button', { name: 'Place order', exact: true })).toBeDisabled();
  await page
    .getByLabel(/^Email\*?$/)
    .fill(`guest-${testInfo.project.name}-${Date.now()}@example.com`);
  await fillAddress(page);
  const total = await page
    .getByRole('table', { name: 'Price summary' })
    .getByRole('row')
    .last()
    .textContent();
  expect(total).toMatch(/Total \(incl\. GST\)₹[\d,]+/);

  const [scrollWidth, width] = await page.evaluate(() => [
    document.documentElement.scrollWidth,
    window.innerWidth,
  ]);
  expect(scrollWidth, 'checkout must not scroll sideways').toBeLessThanOrEqual(width);

  await placeOrder(page);
  const dialog = page.getByRole('dialog', { name: 'Simulated payment' });
  await expect(dialog.getByText('no money moves')).toBeVisible();
  await dialog.getByRole('button', { name: 'Pay (simulated)' }).click();

  await expect(page).toHaveURL(/\/order-confirmation\/ANV-\d{6}-[A-Z0-9]{6}$/);
  await expect(
    page.getByRole('heading', { level: 1, name: 'Thank you — your order is confirmed' }),
  ).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Items' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Om Pendant' })).toBeVisible();
  await expect(page.getByText('Order confirmed', { exact: true })).toBeVisible();

  // The cart was converted into the order.
  await page.reload();
  await expect(
    page.getByRole('heading', { level: 1, name: 'Thank you — your order is confirmed' }),
  ).toBeVisible();

  await cancelOrder(page);
  await expect(page.getByText('Refund requested').first()).toBeVisible();
});

test('a failed payment can be retried', async ({ page, isMobile }, testInfo) => {
  await addOmPendant(page, isMobile);
  await page.goto('/checkout');
  await page
    .getByLabel(/^Email\*?$/)
    .fill(`retry-${testInfo.project.name}-${Date.now()}@example.com`);
  await fillAddress(page);
  await placeOrder(page);

  await page
    .getByRole('dialog', { name: 'Simulated payment' })
    .getByRole('button', { name: 'Simulate a failed payment' })
    .click();
  await expect(page.getByText('The simulated payment was declined.')).toBeVisible();
  await expect(page.getByText(/is saved and your pieces are reserved/)).toBeVisible();

  await page.getByRole('button', { name: 'Try payment again' }).click();
  await page
    .getByRole('dialog', { name: 'Simulated payment' })
    .getByRole('button', { name: 'Pay (simulated)' })
    .click();
  await expect(
    page.getByRole('heading', { level: 1, name: 'Thank you — your order is confirmed' }),
  ).toBeVisible();
  await expect(page.getByText("Payment didn't go through")).toBeVisible();

  await cancelOrder(page);
});

test('signed-in customer checks out and finds the order in their account', async ({
  page,
  isMobile,
}, testInfo) => {
  await page.goto('/register');
  await page.getByLabel(/^Full name/).fill('Ravi Kumar');
  await page
    .getByLabel(/^Email\*?$/)
    .fill(`buyer-${testInfo.project.name}-${Date.now()}@example.com`);
  await page.getByLabel(/^Password/).fill('a long e2e passphrase');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/\/account$/);

  await addOmPendant(page, isMobile);
  await page.goto('/checkout');
  await expect(page.getByText(/^Signed in as/)).toBeVisible();
  await fillAddress(page);
  await placeOrder(page);
  await page
    .getByRole('dialog', { name: 'Simulated payment' })
    .getByRole('button', { name: 'Pay (simulated)' })
    .click();
  await expect(
    page.getByRole('heading', { level: 1, name: 'Thank you — your order is confirmed' }),
  ).toBeVisible();
  const reference = page.url().split('/').pop() ?? '';

  await page.getByRole('link', { name: 'All my orders' }).click();
  await expect(page).toHaveURL(/\/account\/orders$/);
  await page.getByRole('link', { name: new RegExp(reference) }).click();
  await expect(page.getByRole('heading', { name: `Order ${reference}` })).toBeVisible();
  await page.getByRole('button', { name: 'Cancel order' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel order' }).click();
  await expect(page.getByText('Cancelled', { exact: true }).first()).toBeVisible();
});
