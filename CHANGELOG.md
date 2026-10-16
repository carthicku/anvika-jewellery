# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Vercel deployment (ADR-0011): root `vercel.json` with two services (Vite frontend + FastAPI),
  security headers/CSP, SPA fallback and cron schedule; `/api/v1/internal/cron/run-jobs` and
  `/refresh-prices` endpoints protected by `CRON_SECRET`; the in-process job loop is skipped on
  Vercel; `DB_PREPARE_STATEMENTS` for Supabase's transaction pooler; start-up checks that Vercel
  deployments use S3 storage and one proxy hop; backend `pyproject.toml` now reads dependencies from
  the lock file; default store name for builds without `VITE_STORE_NAME`.

### Changed
- Brand wordmark: header and footer now use a vector logo (`components/brand/Logo.tsx`) following
  the reference sheet in `frontend/images/` — thin geometric lowercase "anvika" with a stacked-dots
  "i" and "FINE JEWELLERY" tucked under "n…a". Drawn as shapes (not the image file), follows
  `currentColor`, no font download. The work-in-progress Google Fonts links were removed (the
  production CSP only allows self-hosted fonts).

### Added
- Home page: scroll-scrubbed 3D hero — scattered diamonds travel along curved paths into a gold
  necklace while the hero is pinned (settings and chain links form progressively); scrolling back
  takes it apart along the exact same frames. Reduced motion shows the finished necklace as a
  still. Development prototype at `/lab/necklace` (dev builds only). ADR-0010.
- Phase 8 (launch preparation): `robots.txt` with `ALLOW_SEARCH_INDEXING` (off by default);
  operations commands `verify-integrity`, `verify-rls`, `catalogue-report [--samples]`,
  `send-test-email`; backend `Dockerfile`, `deploy/Caddyfile` (HTTPS, CSP, security headers,
  caching) and `deploy/docker-compose.prod.yml`; E2E journeys J6/J7/J9/J12 and a Playwright config
  for running the suite against a built site; `scripts/perf_catalogue.py`; delivery report.

### Fixed
- Product filter counts returned an error (500) when searching.
- Product pages could show stock/prices up to 60 s old (now always revalidated).
- Pages jumped while loading (late announcement bar, footer pushed down): layout shift ≈ 0 now.
- Accessibility: invalid `aria-label` on the loading grid; heading order on listing pages.

### Added (earlier)
- Phase 7 (after-sales): customers can ask for a return or exchange of delivered pieces within
  each piece's window; staff approve/reject, mark items received (choosing which go back into
  stock) and refund through the normal refund flow, with emails at each step. Verified-purchase
  product reviews with staff moderation; only approved reviews are shown and only they feed the
  rating summary and structured data. Dashboard shows open returns and reviews to moderate.
- Phase 7 (admin): dashboard with net sales and work queues; order management (prepare, ship with
  tracking, deliver, cancel, payment-review resolution, partial/full refunds sent to the payment
  provider, internal notes); product management with variants, photo uploads (re-encoded WebP),
  live price preview, publish/archive; categories and collections; audited stock adjustments and
  movement log; gold rates with price-impact preview and large-change confirmation; customers;
  enquiries; discounts and coupons; delivery methods and PIN-code zones; content page editor;
  store/announcement/GST/gold-rate-policy settings; staff management; audit log viewer.
- Phase 6: checkout (guest or signed-in, saved addresses, delivery options by PIN code, billing
  address, order note, terms), idempotent order creation with stock reservation and total
  confirmation, Razorpay REST integration and a development payment simulator, signature +
  provider verification, webhooks, failure/retry, expiry and reconciliation job
  (`reconcile-payments` CLI), late-capture handling, customer cancellation with restock and refund
  request, order confirmation page (guest private link), account order history and detail with
  timeline, order confirmation/cancellation emails, optional stale-gold-rate checkout block.
- Phase 5: shopping cart for guests and customers (merged at sign-in) with backend-calculated
  totals, quantity limits by stock, price-increase acceptance, price-drop notices, coupons
  (WELCOME5/EXPIRED10 samples), estimated shipping; add to cart / buy now on product pages with a
  sticky mobile bar; header cart count announced to screen readers.
- Phase 4: customer accounts — register, sign in/out (single device or everywhere), email
  verification, password reset/change, signed-in device list, profile, address book, account
  wishlist with guest merge; cookie sessions with rotating refresh tokens; email outbox; permission
  map with admin-route guard; `create-admin` / `deactivate-user` CLI.
- Phases 2 & 3: catalogue data model with RLS, Decimal pricing engine, public catalogue/search/
  facets/PIN-code/content/contact/newsletter/sitemap APIs, idempotent sample seed with original
  placeholder illustrations; premium storefront (home, listings with URL filters, search, product
  page with itemised price breakdown, guest wishlist, contact, content pages), axe-clean, code-split.
- Phase 1 foundation: embedded PostgreSQL launcher (`npm run db:start`); FastAPI app factory with
  production-safe settings, standard error format, CSRF, security headers, body limit, request ids,
  redacting logs, health endpoint, Alembic (first migration with RLS) and pytest fixtures on a real
  PostgreSQL test DB; React 19 / Vite 8 / Tailwind 4 frontend shell with typed API client, routing,
  404 page, Vitest and Playwright smoke tests; `scripts/check.ps1|.sh`, secret scanner, Python lock
  script.
- Phase 0: project documentation (product, design, architecture with ADRs 0001–0009, development,
  operations, quality), task tracker, `CLAUDE.md`, and 11 project-specific Claude Code skills.

### Changed
- Local database launcher enforces UTF-8; database sessions forced to UTC.
- Dev ports set to 5180 (web) and 8010 (API) because 5173/8000 were occupied on the dev machine.
- TypeScript pinned to 5.9 (openapi-typescript requires TS 5); ESLint 10 with `eslint-plugin-jsx-a11y-x`.
