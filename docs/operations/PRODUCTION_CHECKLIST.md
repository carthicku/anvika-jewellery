# Production Launch Checklist

Tick an item only with evidence. Record the date and who verified it.

## Business & legal (owner)
- [ ] Brand name, logo and contact details configured (ASSUMPTIONS B1–B3).
- [ ] GSTIN, registered address and invoice requirements confirmed with a CA.
- [ ] GST rates in Admin → Settings confirmed by a tax professional (ASSUMPTIONS P3).
- [ ] All policy pages reviewed and approved (shipping, returns, refunds, privacy, terms). Draft
      flags removed.
- [ ] Hallmark / HUID / certification data entered only where verified.
- [ ] All sample products, images, coupons and illustrative gold rates removed or replaced
      (`python -m app.cli catalogue-report --samples` returns nothing).
- [ ] Real gold rates entered with source notes.

## Configuration & secrets
- [ ] `APP_ENV=production`; the app refuses the simulator and weak secrets (verified at start-up).
- [ ] `SECRET_KEY` freshly generated (≥ 48 chars) and stored only in the secret manager.
- [ ] `ALLOWED_ORIGINS`, `PUBLIC_SITE_URL` set to the real HTTPS domain.
- [ ] `COOKIE_SECURE=true`. HSTS enabled at the proxy.
- [ ] No `.env` or secret in Git (`scripts/check-secrets` clean, plus GitHub secret scanning enabled).
- [ ] Supabase Data API disabled; RLS enabled on all tables (`python -m app.cli verify-rls`).

## Payments
- [ ] Full test-mode purchase on staging with Razorpay **test** keys: success, failure, retry, refund.
- [ ] Webhook configured (URL, secret, events) and a test delivery shows 200.
- [ ] Live keys installed only after the Razorpay account is activated. One small live transaction
      made and refunded.
- [ ] Razorpay host names in the CSP checked against current Razorpay documentation.

## Email & shipping
- [ ] SMTP configured, sending domain verified (SPF, DKIM, DMARC). A test email is received in Gmail
      and not in spam.
- [ ] Shipping methods, fees and serviceable zones reviewed.

## Data safety
- [ ] Backups enabled; a restore has been tested on a scratch database.
- [ ] `alembic upgrade head` applied; `alembic check` clean.

## Quality
- [ ] `scripts/check` all green (lint, types, unit, API tests) — results recorded in TEST_RESULTS.md.
- [ ] Playwright journeys J1–J12 pass against staging.
- [ ] Accessibility: axe scans pass, plus a manual keyboard pass of checkout.
- [ ] Lighthouse (mobile) on home, listing and product pages recorded in PERFORMANCE_REVIEW.md.
- [ ] `pip-audit` and `npm audit --omit=dev` reviewed; no known high/critical issues unaddressed.
- [ ] Security review items in SECURITY_REVIEW.md resolved or explicitly accepted.

## Go-live
- [ ] The first administrator was created with `create-admin`; staff accounts were given least
      privilege.
- [ ] Uptime monitoring and alert contacts configured.
- [ ] `robots.txt` allows the storefront and disallows `/account`, `/checkout`, `/admin`, `/cart`.
      Sitemap submitted to Google Search Console.
- [ ] Post-deploy smoke test: home, product, add to cart, checkout up to payment, admin login.
