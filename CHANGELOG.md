# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Phase 1 foundation: embedded PostgreSQL launcher (`npm run db:start`); FastAPI app factory with
  production-safe settings, standard error format, CSRF, security headers, body limit, request ids,
  redacting logs, health endpoint, Alembic (first migration with RLS) and pytest fixtures on a real
  PostgreSQL test DB; React 19 / Vite 8 / Tailwind 4 frontend shell with typed API client, routing,
  404 page, Vitest and Playwright smoke tests; `scripts/check.ps1|.sh`, secret scanner, Python lock
  script.
- Phase 0: project documentation (product, design, architecture with ADRs 0001–0009, development,
  operations, quality), task tracker, `CLAUDE.md`, and 11 project-specific Claude Code skills.

### Changed
- Dev ports set to 5180 (web) and 8010 (API) because 5173/8000 were occupied on the dev machine.
- TypeScript pinned to 5.9 (openapi-typescript requires TS 5); ESLint 10 with `eslint-plugin-jsx-a11y-x`.
