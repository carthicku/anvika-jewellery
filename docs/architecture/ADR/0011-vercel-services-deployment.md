# ADR-0011: Deploying on Vercel with Services (static SPA + FastAPI function)

- Status: Accepted (Vercel Services is a **beta** feature — see Consequences)
- Date: 2026-10-16

## Context
The owner wants to host the store on Vercel. The store is one repository with a Vite SPA
(`frontend/`) and a FastAPI backend (`backend/`) that must share one origin (ADR-0003: cookie auth
and CSRF rely on it). The original plan (ADR/DEPLOYMENT.md) was a small VM with Caddy and Docker.
Vercel runs the backend as serverless functions, which changes four things: no long-lived process
(so no in-process job loop), a read-only disk (so no local photo storage), a 4.5 MB request body
limit, and many short-lived instances (so database connections must stay few).

## Decision
* **One Vercel project, two services** (`vercel.json` at the repo root): `web` (`frontend/`, Vite)
  and `api` (`backend/`, FastAPI, entrypoint `app.main:app`). Top-level rewrites send `/api/*`,
  `/sitemap.xml` and `/robots.txt` to `api`, everything else to `web`. The API receives the original
  path (`/api/v1/...`), so the application code is unchanged and the origin stays single.
* **Headers**: the security headers and CSP that `deploy/Caddyfile` sets are repeated in the `web`
  service's `headers`; the API sets its own through `SecurityHeadersMiddleware`.
* **Background jobs**: the in-process loop is skipped when the `VERCEL` variable is present
  (`job_loop_enabled`). Vercel Cron calls `GET /api/v1/internal/cron/run-jobs` every minute and
  `/refresh-prices` every 15 minutes. Both require `Authorization: Bearer $CRON_SECRET` (Vercel
  sends it automatically) and do not exist when `CRON_SECRET` is empty. The work is the same
  idempotent, `SKIP LOCKED` code as `python -m app.cli run-jobs`, so duplicate or missed cron
  deliveries are harmless.
* **Storage**: `STORAGE_BACKEND=s3` is mandatory on Vercel (start-up refuses `local`).
* **Database**: Supabase *transaction* pooler (port 6543) with `DB_POOL_SIZE=1`,
  `DB_MAX_OVERFLOW=0` and `DB_PREPARE_STATEMENTS=false` (transaction poolers can't keep
  server-side prepared statements).
* **Client IPs**: `TRUSTED_PROXY_COUNT=1` is mandatory on Vercel (start-up refuses anything else):
  Vercel sets `X-Forwarded-For` to the visitor, so per-IP rate limits and audit logs stay correct.
* **Dependencies**: `backend/pyproject.toml` reads its dependency list from the generated
  `requirements.txt` (`dynamic`), so Vercel (which prefers `pyproject.toml`) and Docker use the same
  pinned versions. Python 3.13 via `backend/.python-version`.
* The VM/Docker/Caddy files stay as the alternative deployment.

## Consequences
* **Beta**: Vercel Services may change. Fallback: two Vercel projects (frontend + API) with an
  `/api` rewrite, or the VM option; the application code doesn't depend on either.
* **Photo uploads are limited to 4.5 MB** by Vercel (the app allows 10 MB). Resize photos before
  uploading, or upload larger ones later through a direct-to-storage flow (not built).
* **Cron frequency**: per-minute schedules need the Vercel **Pro** plan; Hobby allows only daily
  cron and, per Vercel's terms, is for personal non-commercial use. A store should use Pro. Without
  frequent runs, unpaid orders keep stock reserved until the next run (the 30-minute payment window
  is only enforced when the job runs).
* Cold starts add latency to the first request after idle time (Fluid compute reduces this).
* Migrations are **not** run on deploy. Run `alembic upgrade head` against Supabase from a trusted
  machine before promoting a release that changes the schema.
* Cron wiring under Services (top-level `crons` routed through the service rewrites) could not be
  exercised locally; verify on the first preview deployment (Vercel dashboard → Cron Jobs → Run).
