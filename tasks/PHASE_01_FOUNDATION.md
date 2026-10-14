# Phase 1 — Foundation  ✅ complete (2026-10-14)

Goal: both apps start locally, talk to each other, and basic checks pass.

## Tasks
### Tooling
- [x] Root `package.json` with `db:start` (embedded PostgreSQL 17.10 on :54329, creates `anvika_dev` + `anvika_test`)
- [x] `docker-compose.yml` (db + mailpit) for Docker users — **unverified locally (no Docker)**
- [x] `scripts/check.ps1` + `scripts/check.sh` (docs, secrets, lint, types, migrations, tests, build)
- [x] `scripts/check-secrets.py` (self-tested with planted secrets)
- [x] `scripts/lock_python.py` (full Python lock files from `requirements*.in`)

### Backend
- [x] `pyproject.toml` (ruff incl. bandit rules, mypy strict, pytest) + locked `requirements.txt` / `requirements-dev.txt`
- [x] `app/core/config.py` — Settings with production validation (secrets, simulator ban, secure cookies, https origins, email backend)
- [x] `app/core/db.py` — engine, session factory, `get_db`
- [x] `app/core/errors.py` — `AppError` hierarchy + handlers → standard error JSON (incl. validation, 404, 500 without leaks)
- [x] `app/core/logging.py` — text/JSON logging, redaction, request-context filter
- [x] `app/core/middleware.py` — request id + access log, security headers, body size limit, CSRF (double-submit + Origin check)
- [x] `app/main.py` — app factory, lifespan, CORS from settings, `/api/v1/health` (+ `?deep=true`), docs off in production
- [x] Alembic configured (naming convention, settings-driven URL); first migration (store_settings, audit_logs, rate_limit_buckets + RLS)
- [x] `app/cli.py` — command registry + `export-openapi`
- [x] pytest fixtures: `_test` DB guard, schema rebuilt from migrations, per-test rollback, CSRF-aware client
- [x] Tests: health, error format (404/409/422/500), CSRF (missing, mismatched, valid, foreign origin, webhook exemption), headers, request id, body limit, settings validation, money helpers

### Frontend
- [x] Vite 8 + React 19 + TypeScript 5.9 strict (5.9 because openapi-typescript requires TS 5), `@/` alias, dev proxy
- [x] Tailwind v4 design tokens + self-hosted fonts
- [x] ESLint 10 (typescript-eslint strict-type-checked, react-hooks, jsx-a11y-x, bans `href="#"` and `parseFloat`) + Prettier
- [x] Router (React Router 8 data mode) with root layout (skip link, focus on navigation), home, 404, route error page
- [x] Typed API client (`openapi-fetch`) with CSRF header, one-time session refresh retry, `ApiError`; `gen:api` script
- [x] TanStack Query provider with sensible retry policy
- [x] Vitest + Testing Library setup with fetch mock helper; Playwright config (desktop + mobile) with smoke tests

## Environment notes discovered
- Ports 8000 and 5173 are used by other software on the dev machine → project defaults are **API 8010**, **web 5180**.
- npm 11 blocks dependency install scripts by default; not needed so far.

## Acceptance — met
`npm run db:start`, `alembic upgrade head`, `uvicorn` (:8010) and `npm run dev` (:5180) run; the home page shows
"API connected"; `scripts/check.ps1` passes; Playwright smoke passes on desktop + mobile. See TEST_RESULTS.md.
