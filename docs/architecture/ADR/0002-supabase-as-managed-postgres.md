# ADR-0002: Supabase as managed PostgreSQL, not as the auth provider

- Status: Accepted
- Date: 2026-10-14

## Context
The owner selected Supabase as the database. Supabase also offers Auth, auto-generated REST APIs
(PostgREST) and Storage. The specification requires the FastAPI backend to own authentication,
authorization, pricing, inventory and payment verification, and forbids trusting the browser.

## Decision
- Use Supabase **only as a managed PostgreSQL 17 host** (region `ap-south-1` Mumbai recommended).
- The backend connects with SQLAlchemy through the Supabase **session pooler** connection string
  (port 5432). The transaction pooler (port 6543) is not used because it does not support
  prepared statements by default.
- Supabase Auth and the auto-generated Data API are **not** used. The `public` schema tables are
  only reachable through our backend. Row Level Security is enabled on all application tables with
  no policies (deny-all for Supabase's `anon`/`authenticated` roles) as defence in depth, and the
  Data API should be disabled in the Supabase dashboard — see `docs/operations/DEPLOYMENT.md`.
- Supabase Storage (S3-compatible) may be used for product images in production through the
  storage abstraction in `backend/app/services/storage.py`.

## Consequences
- The application is portable to any PostgreSQL host.
- Supabase's anon key is never needed by the frontend.
- Migrations are run by Alembic, not the Supabase dashboard.
