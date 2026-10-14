# Phase 1 — Foundation

Goal: both apps start locally, talk to each other, and basic checks pass.

## Tasks
### Tooling
- [ ] Root `package.json` with `db:start` (embedded PostgreSQL 17 on :54329, creates `anvika_dev` + `anvika_test`)
- [ ] `docker-compose.yml` (db + mailpit) for Docker users (unverified locally)
- [ ] `scripts/check.ps1` + `scripts/check.sh` (lint, types, tests for both apps)
- [ ] `scripts/check-secrets.py` (simple regex scan for keys/passwords in tracked files)

### Backend
- [ ] `backend/pyproject.toml` (ruff, mypy, pytest config) + pinned `requirements.txt` / `requirements-dev.txt`
- [ ] `app/core/config.py` — Settings with production validation (secrets, simulator ban, secure cookies)
- [ ] `app/core/db.py` — engine, session factory, `get_db`
- [ ] `app/core/errors.py` — `AppError` hierarchy + handlers → standard error JSON (incl. validation errors)
- [ ] `app/core/logging.py` — JSON/text logging, redaction, request id middleware
- [ ] `app/core/security_headers.py` — security headers middleware
- [ ] `app/core/csrf.py` — double-submit CSRF middleware
- [ ] Body size limit middleware
- [ ] `app/main.py` — app factory, CORS from settings, `/api/v1/health` (+ `?deep=1`), docs disabled in production
- [ ] Alembic configured (naming convention, `env.py` reads settings); baseline migration
- [ ] `app/cli.py` — command skeleton (`export-openapi`, `run-jobs` placeholder-free commands only)
- [ ] pytest fixtures: test DB guard (`_test` suffix), schema reset + migrations, TestClient with CSRF helper
- [ ] Tests: health, error format (404/422/500), CSRF rejection, security headers, settings validation

### Frontend
- [ ] Vite + React 19 + TS 6.0 strict scaffold, `@/` alias, Vite proxy for `/api` `/media` `/sitemap.xml`
- [ ] Tailwind v4 + token stub, fonts via @fontsource
- [ ] ESLint (typescript-eslint, react-hooks, jsx-a11y) + Prettier
- [ ] Router with layout, placeholder-free route shells for every route group, 404 page
- [ ] API client (`openapi-fetch`) with CSRF header + one-time refresh retry; `gen:api` script
- [ ] TanStack Query provider
- [ ] Vitest + Testing Library setup with a first test; Playwright config with a smoke test

## Acceptance
- `npm run db:start`, `alembic upgrade head`, `uvicorn` and `npm run dev` all run; the frontend shows the
  backend health status in development.
- `scripts/check` passes. Results recorded in TEST_RESULTS.md.
