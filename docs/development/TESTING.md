# Testing

Plan and coverage targets: [`docs/quality/TEST_PLAN.md`](../quality/TEST_PLAN.md). Latest results:
[`docs/quality/TEST_RESULTS.md`](../quality/TEST_RESULTS.md).

## Backend (pytest)
Prerequisite: the local database is running (`npm run db:start`).
```bash
cd backend
.venv/Scripts/python -m pytest                 # everything
.venv/Scripts/python -m pytest tests/unit      # fast, no database
.venv/Scripts/python -m pytest -k pricing -x   # only tests whose names contain "pricing"; stop at first failure
.venv/Scripts/python -m pytest --cov=app --cov-report=term-missing
```
How it works:
* `tests/conftest.py` connects to `TEST_DATABASE_URL`, **refuses to run unless the database name ends
  with `_test`**, drops and recreates the `public` schema once per test session, and runs all Alembic
  migrations (so migrations are tested too).
* Each API test runs inside a transaction that is rolled back afterwards, so tests don't affect each
  other. Concurrency tests that need real commits use a separate fixture that truncates the tables
  they touch.
* External services are never called: Razorpay is mocked with `httpx.MockTransport`; email uses the
  `memory` backend.

## Frontend unit/component tests (Vitest + Testing Library)
```bash
cd frontend
npm test            # run once
npm run test:watch  # re-run on save
```

## End-to-end (Playwright)
Prerequisites: DB running, migrations applied, seed loaded, Playwright's Chromium installed
(`npx playwright install chromium`), and the backend running **with rate limiting switched off** (the
suite registers and signs in many times; the limits themselves are covered by API tests):
```bash
cd backend
RATE_LIMIT_ENABLED=false PAYMENT_PROVIDER=simulator .venv/Scripts/python -m uvicorn app.main:app --port 8010
# PowerShell: $env:RATE_LIMIT_ENABLED='false'; .venv/Scripts/python -m uvicorn app.main:app --port 8010
```
```bash
cd frontend
npm run e2e          # starts the Vite dev server automatically; backend must already be running
npm run e2e -- --ui  # interactive mode
```
E2E tests create their own customers through the API (`/auth/register`) and use seeded products.
They never perform real financial transactions: checkout tests pay with the development simulator,
then cancel each order, which puts the piece back in stock — so repeated runs don't use up the
sample catalogue.

## Static checks
| Check | Command |
|-------|---------|
| Python lint/format | `ruff check . && ruff format --check .` |
| Python types | `mypy app` |
| TS types | `npm run typecheck` |
| TS lint | `npm run lint` |
| Everything | `scripts/check.ps1` / `scripts/check.sh` |

## Writing good tests
* Test behaviour through public interfaces (HTTP API, rendered UI), not private helpers, except for
  the pricing engine whose pure functions are the contract.
* Every bug fix gets a test that fails before the fix.
* Never mark a feature ✅ in FEATURE_MATRIX without naming the test that proves it.
