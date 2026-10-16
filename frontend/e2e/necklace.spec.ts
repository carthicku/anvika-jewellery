import { expect, test, type Page } from '@playwright/test';

declare global {
  interface Window {
    /** Keeps the WebGL drawing buffer so the canvas can be read back (see NecklaceStage). */
    __NECKLACE_CAPTURE__?: boolean;
  }
}

/*
 * Scroll-scrubbed necklace hero: forward and backward scrolling, pinning, resizing and reduced
 * motion. Pixels are read from the WebGL canvas (window.__NECKLACE_CAPTURE__ keeps the drawing
 * buffer), so these tests check what is actually drawn, not just the progress number.
 *
 * Runs on the development prototype (/lab/necklace) and on the home page. The prototype route
 * only exists in development builds, so it is skipped when the suite runs against a production
 * build (playwright.prod.config.ts).
 */
const PIN_SCREENS = 1.6; // must match NecklaceStage.PIN_SCREENS
const HERO_PATHS = ['/lab/necklace', '/'];

const hero = (page: Page) => page.locator('[data-necklace-hero]');

/** Whether this build renders the hero at the current URL (the prototype is dev-only). */
const hasHero = (page: Page) =>
  hero(page)
    .waitFor({ state: 'attached', timeout: 15_000 })
    .then(() => true)
    .catch(() => false);

async function open(page: Page, path: string) {
  await page.addInitScript(() => {
    window.__NECKLACE_CAPTURE__ = true;
  });
  const response = await page.goto(path);
  return response;
}

/** Scroll position where the pin starts and the pinned distance, measured from the layout. */
async function pinGeometry(page: Page) {
  return page.evaluate((screens) => {
    const section = document.querySelector<HTMLElement>('[data-necklace-hero]');
    const header = document.querySelector<HTMLElement>('body > #root header');
    if (!section || !header) throw new Error('hero or header missing');
    const parent = section.parentElement;
    const anchor = parent?.classList.contains('pin-spacer') ? parent : section;
    const start = anchor.getBoundingClientRect().top + window.scrollY - header.offsetHeight;
    return {
      start,
      distance: Math.round(window.innerHeight * screens),
      header: header.offsetHeight,
    };
  }, PIN_SCREENS);
}

const progressOf = async (page: Page) => Number(await hero(page).getAttribute('data-progress'));

/** Scroll to progress q and wait until the scrubbed animation has settled exactly there. */
async function scrollToProgress(page: Page, q: number) {
  const { start, distance } = await pinGeometry(page);
  await page.evaluate(
    (y) => {
      window.scrollTo(0, y);
    },
    start + q * distance,
  );
  await expect.poll(() => progressOf(page), { timeout: 10_000 }).toBeCloseTo(q, 3);
  // The scrub eases towards the target; wait until it has fully stopped so frames are comparable.
  await expect
    .poll(
      async () => {
        const before = await hero(page).getAttribute('data-progress');
        await page.waitForTimeout(250);
        return before === (await hero(page).getAttribute('data-progress'));
      },
      { timeout: 10_000 },
    )
    .toBe(true);
}

/** A small RGBA thumbnail of the canvas after the next rendered frame. */
async function capture(page: Page): Promise<number[]> {
  return page.evaluate(async () => {
    await new Promise((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(resolve));
    });
    const canvas = document.querySelector<HTMLCanvasElement>('[data-necklace-hero] canvas');
    if (!canvas) throw new Error('no canvas');
    const thumb = document.createElement('canvas');
    thumb.width = 96;
    thumb.height = Math.max(1, Math.round((96 * canvas.height) / canvas.width));
    const context = thumb.getContext('2d');
    if (!context) throw new Error('no 2d context');
    context.drawImage(canvas, 0, 0, thumb.width, thumb.height);
    return Array.from(context.getImageData(0, 0, thumb.width, thumb.height).data);
  });
}

const difference = (a: number[], b: number[]) =>
  a.reduce((sum, value, i) => sum + Math.abs(value - (b[i] ?? 0)), 0) / a.length;

/** Share of thumbnail pixels that are drawn (opaque): stones, settings and chain. */
const coverage = (pixels: number[]) => {
  let drawn = 0;
  for (let i = 3; i < pixels.length; i += 4) if ((pixels[i] ?? 0) > 40) drawn++;
  return drawn / (pixels.length / 4);
};

for (const path of HERO_PATHS) {
  test.describe(`necklace hero on ${path}`, () => {
    test.beforeEach(async ({ page }) => {
      const response = await open(page, path);
      const exists = await hasHero(page);
      test.skip(!response?.ok() || !exists, `${path} has no necklace hero in this build`);
      await expect(hero(page)).toHaveAttribute('data-necklace-mode', 'scroll', {
        timeout: 30_000,
      });
    });

    test('nothing moves until the visitor scrolls (no autoplay)', async ({ page }) => {
      const first = await capture(page);
      expect(coverage(first)).toBeGreaterThan(0.002); // scattered diamonds are drawn
      await page.waitForTimeout(1500);
      expect(await progressOf(page)).toBe(0);
      expect(difference(first, await capture(page))).toBeLessThan(0.01);
    });

    test('forward assembles, backward disassembles along exactly the same frames', async ({
      page,
    }) => {
      const scattered = await capture(page);
      await scrollToProgress(page, 0.5);
      const halfwayForward = await capture(page);
      await scrollToProgress(page, 1);
      const assembled = await capture(page);
      expect(difference(scattered, assembled)).toBeGreaterThan(1);
      expect(coverage(assembled)).toBeGreaterThan(coverage(scattered)); // gold chain + settings

      await scrollToProgress(page, 0.5);
      const halfwayBack = await capture(page);
      await scrollToProgress(page, 0);
      const scatteredAgain = await capture(page);

      expect(difference(halfwayForward, halfwayBack)).toBeLessThan(0.01);
      expect(difference(scattered, scatteredAgain)).toBeLessThan(0.01);
    });

    test('reversing step by step never resets, jumps or replays', async ({ page }) => {
      await scrollToProgress(page, 1);
      const { start, distance } = await pinGeometry(page);
      const seen: number[] = [];
      for (let q = 0.9; q >= -0.001; q -= 0.1) {
        await page.evaluate(
          (y) => {
            window.scrollTo(0, y);
          },
          start + q * distance,
        );
        await page.waitForTimeout(120); // mid-scrub, deliberately not settled
        seen.push(await progressOf(page));
      }
      for (let i = 1; i < seen.length; i++) {
        expect(seen[i], `step ${String(i)}: ${seen.join(', ')}`).toBeLessThanOrEqual(
          (seen[i - 1] ?? 1) + 1e-3,
        );
      }
      expect(seen[0]).toBeGreaterThan(0.6); // still near the end after the first step back
      await expect.poll(() => progressOf(page), { timeout: 10_000 }).toBe(0);
    });

    test('the hero stays pinned below the header while the necklace assembles', async ({
      page,
    }) => {
      const { header } = await pinGeometry(page);
      for (const q of [0.25, 0.75]) {
        await scrollToProgress(page, q);
        const top = await hero(page).evaluate((el) => el.getBoundingClientRect().top);
        expect(Math.abs(top - header)).toBeLessThanOrEqual(1);
      }
      const { start, distance } = await pinGeometry(page);
      await page.evaluate(
        (y) => {
          window.scrollTo(0, y);
        },
        start + distance + 300,
      );
      await expect.poll(() => progressOf(page)).toBe(1);
      const after = await hero(page).evaluate((el) => el.getBoundingClientRect().top);
      expect(after).toBeLessThan(header - 200); // released and scrolled on
    });

    test('resizing mid-animation keeps working without sideways scrolling', async ({
      page,
      isMobile,
    }) => {
      test.skip(isMobile, 'viewport sizes are set on the desktop project');
      await scrollToProgress(page, 0.5);
      for (const size of [
        { width: 820, height: 1000 },
        { width: 390, height: 780 },
        { width: 1440, height: 860 },
      ]) {
        await page.setViewportSize(size);
        await page.waitForTimeout(400); // ScrollTrigger refreshes after resize
        const p = await progressOf(page);
        expect(p).toBeGreaterThan(0);
        expect(p).toBeLessThan(1);
        const [scrollWidth, innerWidth, canvasWidth] = await page.evaluate(() => [
          document.documentElement.scrollWidth,
          window.innerWidth,
          document.querySelector('[data-necklace-hero] canvas')?.getBoundingClientRect().width ?? 0,
        ]);
        expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
        expect(Math.abs(canvasWidth - innerWidth)).toBeLessThanOrEqual(1);
        expect(coverage(await capture(page))).toBeGreaterThan(0.002);
      }
      await scrollToProgress(page, 1);
      await scrollToProgress(page, 0);
    });

    test('switching "reduce motion" on and off mid-scroll is handled live', async ({ page }) => {
      await scrollToProgress(page, 0.4);
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await expect(hero(page)).toHaveAttribute('data-necklace-mode', 'static');
      await expect(hero(page)).toHaveAttribute('data-progress', '1.000');
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await expect(hero(page)).toHaveAttribute('data-necklace-mode', 'scroll');
      await scrollToProgress(page, 0);
      await scrollToProgress(page, 1);
    });
  });

  test(`reduced motion on ${path}: a still of the finished necklace, no pin, no scrub`, async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    const response = await open(page, path);
    test.skip(!response?.ok() || !(await hasHero(page)), `${path} has no hero here`);
    await expect(hero(page)).toHaveAttribute('data-necklace-mode', 'static', { timeout: 30_000 });
    await expect(hero(page)).toHaveAttribute('data-progress', '1.000');
    const pinned = await hero(page).evaluate(
      (el) => el.parentElement?.classList.contains('pin-spacer') ?? false,
    );
    expect(pinned).toBe(false);
    const still = await capture(page);
    expect(coverage(still)).toBeGreaterThan(0.01); // the necklace is drawn
    const top = await hero(page).evaluate((el) => el.getBoundingClientRect().top);
    await page.evaluate(() => {
      window.scrollBy(0, 300);
    });
    await expect
      .poll(() => hero(page).evaluate((el) => el.getBoundingClientRect().top))
      .toBeLessThan(top - 250); // scrolls away normally
    expect(await hero(page).getAttribute('data-progress')).toBe('1.000');
  });
}
