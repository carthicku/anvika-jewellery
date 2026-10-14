# Project Status

**Last updated:** 2026-10-14
**Current phase:** Phase 5 — Cart and pricing (next)
**Last verified checkpoint:** Phase 4 — authentication and customer accounts
(`scripts/check.ps1` all green; 168 backend tests, 33 frontend tests, 30 E2E runs ×3, axe clean)

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
| No sideways scrolling on phones | `e2e/smoke.spec.ts` (10 routes) |

## Not yet built
Cart & checkout (Phases 5–6), payments/orders (Phase 6), admin UI (Phase 7), launch prep (Phase 8).
Product pages currently show "Online ordering opens in a later release".

## Local ports
Web **5180**, API **8010**, PostgreSQL **54329** (5173 and 8000 are used by other projects here).

## Blockers / waiting on the owner
Nothing blocks development. Needed before launch: brand details, Razorpay test keys, Supabase
project, SMTP provider, CA review of GST, legal review of policies (ASSUMPTIONS §5).

## Next step
Phase 5: carts (guest cookie + account, merge at sign-in), cart API with backend-calculated totals
(the pricing engine already supports discounts, coupons, GST and rounding), coupons table + seed,
price-change detection/acceptance, quantity stepper, cart page, add-to-cart / buy-now on product pages.

## How to resume
1. Read `CLAUDE.md`, this file, `tasks/PHASE_05_CART_AND_CHECKOUT.md`.
2. Terminal 1: `npm run db:start` (repo root).
3. Terminal 2: `cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8010`
   (for `npm run e2e`, start it with `RATE_LIMIT_ENABLED=false` — see docs/development/TESTING.md).
4. Terminal 3: `cd frontend && npm run dev` → http://localhost:5180.
5. Continue with the first unticked task; finish with `scripts/check.ps1` and `npm run e2e`.
