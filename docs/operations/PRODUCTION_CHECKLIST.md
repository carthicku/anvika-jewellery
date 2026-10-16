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
- [ ] `docker build` of `backend/` succeeds and `docker compose -f deploy/docker-compose.prod.yml up -d`
      starts both containers healthy (never run so far — no Docker on the dev machine).
- [ ] Playwright journeys J1–J12 pass against staging
      (`E2E_BASE_URL=https://staging… npx playwright test -c playwright.prod.config.ts`).
- [ ] Accessibility: axe scans pass, plus a manual keyboard pass of checkout.
- [ ] Lighthouse (mobile) on home, listing and product pages recorded in PERFORMANCE_REVIEW.md.
- [ ] `pip-audit` and `npm audit --omit=dev` reviewed; no known high/critical issues unaddressed.
- [ ] Security review items in SECURITY_REVIEW.md resolved or explicitly accepted.

## If hosting on Vercel (DEPLOYMENT.md §7)
- [ ] Vercel **Pro** plan (per-minute cron; Hobby is non-commercial and daily-cron only).
- [ ] Preview deployment checked: health (deep), a test purchase, an admin photo upload under 4.5 MB,
      and the `run-jobs` cron ran (Settings → Cron Jobs → Run; response `200` with counts).
- [ ] `CRON_SECRET`, `STORAGE_BACKEND=s3`, `TRUSTED_PROXY_COUNT=1`, `DB_POOL_SIZE=1`,
      `DB_MAX_OVERFLOW=0`, `DB_PREPARE_STATEMENTS=false` set; `alembic upgrade head` run on Supabase
      **before** the deploy that needs it.
- [ ] Unpaid orders really expire (place one, wait past the payment window, confirm it expired).

## Go-live
- [ ] The first administrator was created with `create-admin`; staff accounts were given least
      privilege.
- [ ] Uptime monitoring and alert contacts configured; daily `verify-integrity` cron with an alert
      (MONITORING.md).
- [ ] `ALLOW_SEARCH_INDEXING=true` set on the live site only; `/robots.txt` then allows the
      storefront, disallows `/account`, `/checkout`, `/admin`, `/cart` and lists the sitemap.
      Sitemap submitted to Google Search Console.
- [ ] Post-deploy smoke test: home, product, add to cart, checkout up to payment, admin login.

## Walkthrough 2026-10-15 (development machine, before staging)
Boxes above stay unticked until checked in the real environment. What could be checked locally:
| Item | Local result | Still needed |
|------|--------------|--------------|
| Business & legal | Placeholders only; `catalogue-report --samples` lists 31 published sample products (exit 1, as designed) | All owner items |
| `APP_ENV=production` refuses unsafe config | ✅ `test_settings.py` (simulator, weak/missing secrets, insecure cookies refused) | Set real values |
| No secrets in Git | ✅ `scripts/check-secrets.py` clean | Enable GitHub secret scanning |
| RLS on all tables, no policies | ✅ `verify-rls` OK (dev DB); `test_every_application_table_has_row_level_security` | Run `verify-rls` on Supabase; disable the Data API |
| Payments | ✅ simulator + mocked Razorpay API (`test_payments.py`, E2E) | Razorpay test keys on staging; webhook delivery; live activation |
| CSP / headers | ✅ verified behind Caddy locally (E2E with CSP active) | Re-check Razorpay hosts with the real checkout script on staging |
| Email | ✅ outbox, templates, file/memory sinks; `send-test-email` reports the sink honestly | SMTP provider, SPF/DKIM/DMARC, inbox test |
| Backups / restore | ⏳ documented in BACKUP_AND_RESTORE.md, not exercised | Enable Supabase backups; test a restore |
| Migrations | ✅ `alembic upgrade head` on an empty test DB every test run; `alembic check` clean | Run on Supabase before switching traffic |
| Quality gates | ✅ `scripts/check.ps1` green; E2E 62 passed on dev and on the production build behind Caddy; axe clean; Lighthouse recorded; `npm audit`/`pip-audit` clean | Repeat on staging; manual keyboard pass of checkout by a person |
| Data integrity | ✅ `verify-integrity` OK on the dev DB after all E2E runs | Schedule it daily |
| Docker images | ⏳ not built (Docker unavailable) | Build and start on the server/CI |
| robots/indexing | ✅ `/robots.txt` blocks everything by default; private areas disallowed when enabled (tests) | Turn indexing on at launch |
