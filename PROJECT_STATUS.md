# Project Status

**Last updated:** 2026-10-14
**Current phase:** Phase 3 — Database-backed catalogue (next), followed by Phase 2 storefront pages
**Last verified checkpoint:** Phase 1 — Foundation complete (`scripts/check.ps1` all green, E2E smoke 4/4)

## What exists
* Planning documentation (`docs/`), ADRs 0001–0009, task tracker (`tasks/`), `CLAUDE.md`, 11 skills.
* **Backend** (`backend/`): FastAPI app factory, settings with production safety validation, standard
  error format, request-id + access logging with redaction, security headers, body-size limit, CSRF
  middleware, health endpoint, CSRF-token endpoint, Alembic with the first migration (store
  settings, audit log, rate-limit buckets, RLS enabled), CLI (`export-openapi`), pytest fixtures
  against a real PostgreSQL test DB.
* **Frontend** (`frontend/`): Vite 8 + React 19 + TS 5.9 strict, Tailwind v4 design tokens, self-hosted
  fonts, React Router 8 shell (skip link, focus management, 404, error page), typed API client
  (CSRF + session refresh + `ApiError`), TanStack Query, Vitest + Playwright.
* **Tooling**: `npm run db:start` (embedded PostgreSQL 17.10), `scripts/check.ps1|.sh`,
  `scripts/check-secrets.py`, `scripts/check_docs.py`, `scripts/lock_python.py`, optional Docker Compose.

## What works (verified — see docs/quality/TEST_RESULTS.md)
| Item | Evidence |
|------|----------|
| Local PostgreSQL 17.10 | `npm run db:start` |
| Backend foundation | 35 pytest tests; ruff + mypy strict clean; `alembic check` no drift |
| Frontend foundation | 9 Vitest tests; typecheck, lint, format, build clean |
| Frontend ↔ backend via Vite proxy | Playwright smoke (desktop + mobile) shows "API connected" |

## Local ports
Web **5180**, API **8010**, PostgreSQL **54329** (5173 and 8000 are used by other projects here).

## Blockers / waiting on the owner
Nothing blocks development. Needed before launch (see `docs/ASSUMPTIONS_AND_DECISIONS.md` §5):
brand details, Razorpay test keys, Supabase project, SMTP provider, CA review of GST, legal review of
policies.

## Next step
Phase 3 (backend catalogue): catalogue/pricing/content/shipping models + migration, pricing engine
core with unit tests, public catalogue APIs with filters/sort/search/pagination, deterministic seed
with placeholder illustrations, sitemap. Then Phase 2: design-system components and storefront pages
wired to those APIs.

## How to resume
1. Read `CLAUDE.md`, this file, `tasks/PHASE_03_CATALOGUE.md`.
2. Terminal 1: `npm run db:start` (repo root).
3. Terminal 2: `cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8010`.
4. Terminal 3: `cd frontend && npm run dev` → http://localhost:5180.
5. Continue with the first unticked task in the Phase 3 file; finish with `scripts/check.ps1`.
