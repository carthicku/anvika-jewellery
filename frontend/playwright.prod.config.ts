import { defineConfig } from '@playwright/test';

import base from './playwright.config';

/**
 * The same end-to-end suite against a PRODUCTION BUILD behind the production web server
 * (deploy/Caddyfile: CSP, security headers, caching), e.g. a local Caddy on :5190 or a staging
 * site. Never point this at the live store: the tests place (simulated) orders and change sample
 * stock and rates. The backend must use PAYMENT_PROVIDER=simulator and RATE_LIMIT_ENABLED=false.
 *
 *   E2E_BASE_URL=http://localhost:5190 npx playwright test -c playwright.prod.config.ts
 */
export default defineConfig({
  ...base,
  use: { ...base.use, baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5190' },
  webServer: undefined,
  outputDir: 'test-results-prod',
  reporter: [['list']],
});
