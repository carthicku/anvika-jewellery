/** Shared E2E helpers. The admin account and its random password come from e2e/global-setup.ts. */
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { expect, type Browser, type Page } from '@playwright/test';

export const here = dirname(fileURLToPath(import.meta.url));

const credentials = (): { email: string; password: string } =>
  JSON.parse(readFileSync(resolve(here, '.auth/admin.json'), 'utf8')) as {
    email: string;
    password: string;
  };

export async function signInAsAdmin(page: Page, next = '/admin') {
  const { email, password } = credentials();
  await page.goto(`/login?next=${encodeURIComponent(next)}`);
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(new RegExp(`${next}$`));
}

/** A separate signed-in staff browser, so the customer's session stays untouched. */
export async function adminPage(browser: Browser, next = '/admin') {
  const context = await browser.newContext();
  const page = await context.newPage();
  await signInAsAdmin(page, next);
  return { page, close: () => context.close() };
}

/** Change the on-hand stock of one SKU by `delta` through the audited admin screen. */
export async function adjustStock(admin: Page, sku: string, delta: number, reason: string) {
  await admin.goto('/admin/inventory');
  await admin.getByLabel('Search', { exact: false }).fill(sku);
  await admin.getByRole('button', { name: 'Search' }).click();
  await admin
    .getByRole('row', { name: new RegExp(sku) })
    .getByRole('button', { name: 'Adjust…' })
    .click();
  await admin.getByLabel(/^Change/).fill(String(delta));
  await admin.getByLabel(/^Reason/).fill(reason);
  await admin.getByRole('button', { name: 'Save adjustment' }).click();
  await expect(admin.getByText('Stock updated.')).toBeVisible();
}

/** Publish a gold rate through the admin screen (preview first, as staff must). */
export async function setGoldRate(admin: Page, purity: string, rate: string, source: string) {
  await admin.goto('/admin/gold-rates');
  await admin.getByLabel(/^Purity/).selectOption(purity);
  await admin.getByLabel(/^Rate per gram/).fill(rate);
  await admin.getByLabel(/^Source/).fill(source);
  await admin.getByRole('button', { name: 'Preview price changes' }).click();
  await admin.getByRole('button', { name: `Save new ${purity} rate` }).click();
  await expect(admin.getByText(`${purity} rate saved. Prices updated.`)).toBeVisible();
}

/** Add a single-size product to the cart from its page (mobile has a sticky bar button). */
export async function addToCart(page: Page, slug: string, name: string, isMobile: boolean) {
  await page.goto(`/products/${slug}`);
  await (
    isMobile
      ? page.getByRole('button', { name: `Add ${name} to cart` })
      : page.getByRole('button', { name: 'Add to cart', exact: true })
  ).click();
  await expect(page.getByRole('link', { name: /^Cart, [1-9]/ }).first()).toBeVisible();
}
