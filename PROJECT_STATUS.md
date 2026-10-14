# Project Status

**Last updated:** 2026-10-14
**Current phase:** Phase 1 — Foundation (next)
**Last verified checkpoint:** Phase 0 — Discovery & planning complete

## What exists
* Complete planning documentation (`docs/`), ADRs 0001–0009, task tracker (`tasks/`), `CLAUDE.md`,
  and 11 Claude Code skills (`.claude/skills/`).
* No application code yet.

## What works (verified)
| Item | Evidence |
|------|----------|
| Local PostgreSQL 17 via embedded-postgres on this Windows machine | Probe started 17.10 and answered `select version()` (TEST_RESULTS 2026-10-14) |
| Docs/skills structure | `scripts/check_docs.py` (see TEST_RESULTS) |

## Blockers / waiting on the owner
Nothing blocks development. Needed before launch (see `docs/ASSUMPTIONS_AND_DECISIONS.md` §5):
1. Brand name/logo/contact details/GSTIN confirmation.
2. Razorpay **test** keys (for the real sandbox test; development continues with the simulator).
3. Supabase project + connection string (development continues on local PostgreSQL 17).
4. SMTP provider choice; shipping partner (optional).
5. CA review of GST settings; legal review of policies.

## Next step
Phase 1 — Foundation: root tooling (`db:start`), backend skeleton (config, errors, CSRF, headers,
logging, health, Alembic, pytest fixtures), frontend skeleton (Vite/React/TS/Tailwind/Router/Query,
API client, tests). See `tasks/PHASE_01_FOUNDATION.md`.

## How to resume
1. Read `CLAUDE.md`, this file, then `tasks/PHASE_01_FOUNDATION.md`.
2. `npm run db:start` (once Phase 1 has created it) in a background terminal.
3. Continue with the first unticked task.
