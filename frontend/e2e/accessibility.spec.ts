import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const PAGES = [
  '/',
  '/collections',
  '/collections/rings',
  '/products/everyday-gold-band',
  '/gold-buying-guide',
  '/contact',
  '/wishlist',
];

for (const path of PAGES) {
  test(`no serious accessibility violations on ${path}`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze();
    const serious = results.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical',
    );
    expect(
      serious.map(
        (v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(' ')).join(', ')})`,
      ),
    ).toEqual([]);
  });
}

test('keyboard users can reach the main content and open search', async ({ page, isMobile }) => {
  test.skip(isMobile, 'Keyboard flow is checked on desktop');
  const focused = () => page.evaluate(() => (document.activeElement?.textContent ?? '').trim());
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible(); // app has rendered
  await page.keyboard.press('Tab');
  expect(await focused()).toBe('Skip to content'); // first stop, before any other link
  await page.keyboard.press('Tab');
  expect(await focused()).toBe('Search');
  await page.keyboard.press('Enter');
  await expect(page.getByLabel('Search jewellery')).toBeVisible();
  expect(await page.evaluate(() => document.activeElement?.id)).toBe(
    await page.getByLabel('Search jewellery').getAttribute('id'),
  );
  await page.keyboard.press('Escape');
  await expect(page.getByLabel('Search jewellery')).toBeHidden();
  // Focus returns to the button that opened the dialog.
  expect(await focused()).toBe('Search');
});
