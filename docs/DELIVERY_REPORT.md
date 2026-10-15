# Delivery Report — Anvika gold jewellery store

**Date:** 2026-10-15 · **State:** code-complete and verified on the development machine ·
**Not deployed** — the site is not live. Going live needs the owner's accounts and decisions
listed in §5.

"Anvika" is a placeholder brand. Products, photos, gold rates, tax rates, policies, contact details
and the business address are clearly marked sample or placeholder data.

## 1. What has been built
| Area | What a person can do |
|------|----------------------|
| Storefront | Browse collections, filter (category, purity, colour, price, availability), sort, search with suggestions, view product pages with an itemised gold price (gold value, making, wastage, stones, GST), choose sizes, check delivery by PIN code, keep a wishlist |
| Accounts | Register, sign in/out (one device or all), verify email, reset/change password, see signed-in devices, manage addresses, account wishlist (guest wishlist merges at sign-in) |
| Cart & checkout | Guest or account cart; totals always calculated by the server; price rises must be accepted; coupons; delivery options; guest or account checkout; one order per click (idempotent) with stock held during payment |
| Payments | Razorpay (signature + provider check, signed webhooks, duplicate-safe), failed-payment retry, automatic expiry and reconciliation; a payment **simulator** for development only (refused in production) |
| Orders | Confirmation page and emails, order history and tracking, customer cancellation (stock restored, refund requested) |
| After-sales | Return or exchange requests within each piece's window; staff approve/reject, receive (choose what goes back into stock), refund or complete; reviews only from customers whose order was delivered, shown only after staff approve them |
| Admin | Dashboard (net sales from verified payments only, work queues, low stock, stale-rate warning), orders (prepare, ship with tracking, deliver, cancel, refunds sent to the provider, payment-review resolution, notes), products (variants, photo upload re-encoded to WebP, live price preview, publish/archive), categories, collections, inventory with an audited ledger, gold rates with impact preview and large-change confirmation, customers, enquiries, discounts/coupons, delivery methods/zones, content pages, settings (store details, announcement, GST rates), returns, reviews, staff roles, audit log |
| Operations | `verify-integrity`, `verify-rls`, `catalogue-report --samples`, `send-test-email`; production web-server config (Caddy: HTTPS, CSP, security headers, caching), backend container file, compose file; `robots.txt` and sitemap |

Security essentials (details in [SECURITY_MODEL](architecture/SECURITY_MODEL.md) and
[SECURITY_REVIEW](quality/SECURITY_REVIEW.md)): the browser never decides prices, stock, totals or
payment status; an order is paid only after a verified Razorpay payment; every admin endpoint
checks a permission on the server; customers can only reach their own data; passwords use Argon2id;
sessions are HttpOnly cookies with CSRF protection; secrets live only in environment files that are
never committed.

## 2. How it was verified (2026-10-15)
| Check | Result |
|-------|--------|
| `scripts/check.ps1` (lint, types, migrations in sync, backend + frontend tests, production build) | All passed |
| Backend tests (pytest, real PostgreSQL 17) | 308 passed |
| Frontend unit/component tests (Vitest) | 48 passed |
| Browser tests (Playwright, desktop + phone) on the dev server | 62 passed, 4 skipped by design |
| Same browser tests on the **production build behind the production web-server config** (CSP active) | 62 passed, 4 skipped by design |
| Accessibility (axe) on storefront, checkout and admin screens | No serious/critical issues |
| Lighthouse (production build, local) | Accessibility 100, Best practices 100, SEO 100 on indexable pages; Performance desktop 94–99, mobile 79–83 |
| Catalogue API with 1,000 products | p95 ≤ 76 ms in-process (target < 300 ms) |
| Dependency audits | `npm audit`: 0 vulnerabilities; `pip-audit`: none known |
| Data checks on the dev database after all test runs | `verify-integrity` OK, `verify-rls` OK |
| Secret scan | Clean |

Full results, including the failures found on the way and how they were fixed:
[TEST_RESULTS](quality/TEST_RESULTS.md), [PERFORMANCE_REVIEW](quality/PERFORMANCE_REVIEW.md),
[FEATURE_MATRIX](FEATURE_MATRIX.md) (launch criteria L1–L21).

## 3. What has NOT been verified (be aware)
* **Real Razorpay**: only the simulator and a mocked Razorpay API have been used. No real money
  has moved. Needs test keys on a staging site.
* **Docker**: the backend image and compose stack have never been built — Docker isn't installed on
  this machine. Build them on the server or in CI first.
* **Supabase, email delivery (SMTP), S3 photo storage, HTTPS certificates**: not exercised; each
  needs the owner's account.
* **Backups and restore**: documented, not rehearsed.
* **A person's keyboard/screen-reader pass** of checkout: automated checks pass; a human pass is
  still on the checklist.

## 4. Known limitations
Full list: [KNOWN_LIMITATIONS](quality/KNOWN_LIMITATIONS.md). The main ones:
* **No two-factor login for staff** (deferred). Mitigated by rate-limited sign-in, short sessions,
  session revocation on role change and a full audit log — recommended before adding more staff.
* **Mobile first load is slowish** (≈3.5–3.8 s largest paint on simulated slow 4G) because the site
  renders in the browser. Next step: pre-render the public pages.
* No cash on delivery, courier integration, live gold-rate feed, multiple languages or currencies.
* Return shipping (pickup/labels) is arranged by staff outside the system.

## 5. What the owner needs to provide before launch
1. Brand name, logo, contact details, business address, GSTIN.
2. GST rates confirmed by a CA; policies (shipping, returns, refunds, privacy, terms) approved by a
   lawyer — drafts are in Admin → Content.
3. Real products and photos (replace or archive all 31 sample products —
   `catalogue-report --samples` must pass), real gold rates with their source.
4. Accounts: Razorpay (test keys first, live keys after KYC), Supabase (Mumbai region), an SMTP
   provider with a verified sending domain, a domain name and a small server in India.

## 6. How to go live (summary)
Follow [DEPLOYMENT](operations/DEPLOYMENT.md) and tick
[PRODUCTION_CHECKLIST](operations/PRODUCTION_CHECKLIST.md) with evidence:
1. Create the Supabase project, run migrations, `verify-rls`, disable the Data API.
2. Build the backend image and start `deploy/docker-compose.prod.yml` on a **staging** domain with
   Razorpay **test** keys and `ALLOW_SEARCH_INDEXING=false`.
3. Run the browser suite against staging (`playwright.prod.config.ts`), a full test purchase with
   success, failure, retry and refund, and `send-test-email`.
4. Owner content and settings; `catalogue-report --samples` clean.
5. Switch to live keys after Razorpay activation, set `ALLOW_SEARCH_INDEXING=true`, submit the
   sitemap, schedule `verify-integrity` daily, set up uptime alerts.

## 7. Working on it locally
[LOCAL_SETUP](development/LOCAL_SETUP.md) (beginner-friendly), [TESTING](development/TESTING.md),
[CLAUDE.md](../CLAUDE.md) for the command list. Ports: website 5180, API 8010, database 54329.
