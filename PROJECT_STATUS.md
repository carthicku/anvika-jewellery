# Project Status

**Last updated:** 2026-10-15
**Current phase:** Phase 8 — Launch preparation (next)
**Last verified checkpoint:** Phase 7 complete — admin plus returns and reviews
(`scripts/check.ps1` all green; 298 backend tests, 48 frontend tests, 56 E2E passed + 2 skipped by design, axe clean)

## What exists
* Planning documentation, ADRs 0001–0009, task tracker, `CLAUDE.md`, 11 skills.
* **Backend**: FastAPI foundation (settings with production validation, error format, CSRF, headers,
  body limit, logging, rate limiting in PostgreSQL); catalogue/pricing/inventory/shipping/content
  models with RLS; the Decimal **pricing engine** (all models, discounts, coupons, GST per component,
  rupee rounding); public catalogue, search, facets, PIN-code, settings, content, contact, newsletter
  and sitemap APIs; idempotent sample seed (31 products) with original placeholder illustrations.
* **Frontend**: premium design system (tokens with measured contrast, self-hosted fonts), header with
  category nav, search dialog with suggestions, mobile menu, footer with newsletter; home, collections,
  category/collection listings (URL-driven filters, sort, pagination), search, product page (gallery,
  sizes, itemised breakdown with gold rate, PIN-code delivery check, specs, related, recently viewed),
  guest wishlist, contact form and nine editable content pages. Route-level code splitting (initial JS
  150 kB gzip; 93 kB after Phase 4 splitting).
* **Accounts (Phase 4)**: register / sign in / sign out (one device or all), email verification,
  password reset and change, signed-in device list, profile, address book (Indian PIN/state/mobile
  validation), account wishlist with guest merge; HttpOnly cookie sessions with rotating refresh
  tokens; email outbox (development emails are written to `backend/var/mail/`); role→permission map
  and admin-route guard; `create-admin` and `deactivate-user` CLI commands.

* **Cart (Phase 5)**: guest and account carts (merged at sign-in), backend-priced lines and summary
  with estimated shipping, coupons, price-increase acceptance, stock/quantity limits; add to cart and
  buy now on product pages.

* **Checkout & orders (Phase 6)**: checkout for guests and customers, idempotent order creation with
  stock reservation and total confirmation, Razorpay REST client + development simulator, verified
  payments only (signature + provider fetch), webhooks, retry, expiry/reconciliation job, late-capture
  handling, cancellation with restock and refund request, confirmation page, order history, emails.

* **Admin (Phase 7)**: `/admin` for staff — dashboard, orders (fulfil, cancel, refund), products with
  photos and price preview, categories/collections, inventory, gold rates, customers, enquiries,
  discounts/coupons, delivery, content, settings, staff, audit log. Create the first admin with
  `python -m app.cli create-admin`.

* **After-sales (Phase 7)**: return/exchange requests from the order page (eligible pieces, within
  the window from delivery) with staff approve/reject → received (choose what goes back into
  stock) → refund or complete; verified-purchase reviews with moderation (only approved reviews
  are public; rating summary and structured data use approved reviews only).

## What works (verified — see docs/quality/TEST_RESULTS.md)
| Item | Evidence |
|------|----------|
| Pricing engine matches PRICING_ENGINE.md | 37 unit tests incl. the worked example |
| Catalogue filters, sort, search, pagination, facets | `tests/api/test_catalogue.py` |
| Contact/newsletter anti-spam + rate limits | `tests/api/test_content.py` |
| RLS on every table, stock CHECK, UTC sessions | `tests/api/test_database_safety.py` |
| Storefront journeys (browse → filter → product → size → delivery → wishlist; search) | `e2e/browse.spec.ts` on desktop + mobile |
| Accessibility | axe: 0 serious/critical issues on 7 pages; keyboard flow test |
| Accounts & access control | `tests/api/test_auth.py`, `test_account.py`, `test_permissions.py`, `e2e/account.spec.ts` |
| No sideways scrolling on phones | `e2e/smoke.spec.ts` (11 routes), `e2e/cart.spec.ts` |
| Cart, coupons, price-change rules | `tests/api/test_cart.py`, `cart.test.tsx`, `e2e/cart.spec.ts` |
| Admin API and screens | `test_admin_ops.py`, `test_admin_catalogue.py`, `test_admin_store.py`, `admin.test.tsx`, `e2e/admin.spec.ts` |
| Returns and reviews | `tests/api/test_aftercare.py`, `checkout.test.tsx` (return form), `admin.test.tsx`, `e2e/admin.spec.ts` (return and review journeys) |
| Checkout, payments, webhooks, expiry, cancellation | `tests/api/test_checkout.py`, `test_payments.py`, `test_inventory_concurrency.py`, `checkout.test.tsx`, `e2e/checkout.spec.ts` |

## Not yet built
Optional staff TOTP (deferred, see KNOWN_LIMITATIONS) and launch prep (Phase 8).
Payments have not yet been run with real Razorpay test keys.

## Local ports
Web **5180**, API **8010**, PostgreSQL **54329** (5173 and 8000 are used by other projects here).

## Blockers / waiting on the owner
Nothing blocks development. Needed before launch: brand details, Razorpay test keys, Supabase
project, SMTP provider, CA review of GST, legal review of policies (ASSUMPTIONS §5).

## Next step
Phase 8 launch prep (`tasks/PHASE_08_POLISH_AND_LAUNCH.md`): remaining E2E journeys, security/performance/SEO
reviews, robots.txt, deployment files, operational CLI checks, production checklist, final report.

## How to resume
1. Read `CLAUDE.md`, this file, `tasks/PHASE_08_POLISH_AND_LAUNCH.md`.
2. Terminal 1: `npm run db:start` (repo root).
3. Terminal 2: `cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8010`
   (for `npm run e2e`, start it with `RATE_LIMIT_ENABLED=false` — see docs/development/TESTING.md).
4. Terminal 3: `cd frontend && npm run dev` → http://localhost:5180.
5. Continue with the first unticked task; finish with `scripts/check.ps1` and `npm run e2e`.
