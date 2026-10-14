---
name: testing-and-qa
description: Use after implementing or changing any feature, before marking a task complete, or when asked about test status. Identifies the unit/API/component/E2E tests required, runs the real test commands, reports actual results, fixes regressions, and updates TEST_RESULTS.md and FEATURE_MATRIX.md.
---

# Testing and QA

Plan: `docs/quality/TEST_PLAN.md`. How to run: `docs/development/TESTING.md`.

## Workflow
1. **Identify** which tests the change needs (TEST_PLAN §2–4). Write missing ones first or alongside.
2. **Prerequisites**: local DB running (`npm run db:start` from the repo root, in the background).
3. **Run** the relevant suites, then everything before declaring a checkpoint:
   ```
   cd backend && .venv/Scripts/python -m pytest -q
   cd backend && .venv/Scripts/python -m ruff check . && .venv/Scripts/python -m mypy app
   cd frontend && npm run typecheck && npm run lint && npm test
   cd frontend && npm run build
   cd frontend && npm run e2e          # when the change affects a user journey
   ```
4. **Read the output.** Report exact counts and failures. Do not summarise "all good" without having
   seen the passing output in this session.
5. **Fix** failures at the root cause. Never weaken an assertion, skip, or `xfail` a test to get green
   without recording why in KNOWN_LIMITATIONS.md.
6. **Record** a dated entry in `docs/quality/TEST_RESULTS.md` (command → result) at each checkpoint,
   and update the `Status`/`Evidence` columns in `docs/FEATURE_MATRIX.md` (✅ only with a named test).

## Quality bar
* Tests assert behaviour visible to users or API clients.
* Each bug fix includes a regression test.
* No test calls real external services or moves real money.
* Flaky tests are bugs: fix them or quarantine them with a note. Never ignore them.
