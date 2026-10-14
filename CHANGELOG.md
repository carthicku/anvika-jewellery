# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
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
