# ADR-0006: Embedded PostgreSQL for local development

- Status: Accepted
- Date: 2026-10-14

## Context
The development machine (Windows 11) has no Docker and no PostgreSQL. Tests must run against real
PostgreSQL because we rely on row locks, CHECK constraints, `NUMERIC`, JSONB and full-text search.
SQLite would hide real bugs.

## Decision
The root `package.json` provides `npm run db:start`, which uses the `embedded-postgres` npm package
(PostgreSQL 17.x binaries, no admin rights needed) to run a server on `127.0.0.1:54329` with data in
`.localdb/`. It creates the `anvika_dev` and `anvika_test` databases. `docker-compose.yml` offers the
same on machines with Docker.

## Consequences
- Local and Supabase production use the same major PostgreSQL version (17).
- The embedded server must be running before backend dev/test commands.
