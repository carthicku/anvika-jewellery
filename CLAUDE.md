# CLAUDE.md — Project instructions for Claude Code

Premium gold jewellery e-commerce store for the Indian market (INR). Working brand name **"Anvika"**
(placeholder, configurable). React SPA + FastAPI modular monolith + PostgreSQL (Supabase in
production).

## Start of every session
1. Read `PROJECT_STATUS.md` (current phase, blockers, next step).
2. Read the task file for the current phase in `tasks/`.
3. Read the architecture/design docs relevant to the work (index below) **before editing code**.
4. Use the matching project skill in `.claude/skills/` (see table).

## Non-negotiable rules
1. **The backend owns business rules**: prices, discounts, totals, stock, order/payment status,
   permissions. Never trust values from the browser. The frontend only displays.
2. **Money is `Decimal`/`NUMERIC`**, serialised as strings. Never `float`.
3. **An order is paid only through `mark_order_paid`** after verified Razorpay evidence. Never fake
   payment success. The simulator is dev/test only.
4. **Every admin endpoint** declares `require_permission(...)`. Customers can only reach their own
   data (404 otherwise).
5. **No secrets** in code, docs, logs, tests, commits or `VITE_*` variables. Real values live in
   git-ignored `.env` files.
6. **No invented business facts**: no fake reviews, certifications, hallmarks, ratings, addresses or
   market gold rates. Use clearly marked placeholders.
7. **Never mark something done without verification.** Run the tests, read the output, record the
   results in `docs/quality/TEST_RESULTS.md`.
8. **No destructive DB operations** outside the test database (the test fixture refuses DB names
   that don't end in `_test`). Schema changes go through Alembic migrations only.
9. No unfinished TODOs in auth, checkout, payments, inventory or pricing code.
10. Keep code beginner-readable; explain important commands in plain language when reporting.

## Skills (`.claude/skills/`)
| Skill | Use when |
|-------|----------|
| `project-architecture` | Deciding where code goes, adding modules/deps/tables |
| `premium-ui-ux` | Any visible UI work or review |
| `react-frontend` | Code in `frontend/` |
| `fastapi-backend` | Code in `backend/` |
| `gold-pricing-engine` | Anything touching prices, rates, tax, discounts |
| `secure-payments-and-orders` | Checkout, Razorpay, webhooks, order states, refunds |
| `inventory-management` | Stock, reservations, adjustments |
| `testing-and-qa` | Before marking anything complete |
| `security-review` | Auth, inputs, uploads, secrets, headers, releases |
| `documentation-maintainer` | After every meaningful change / checkpoint |
| `deployment-readiness` | Before staging/production deploys |

## Repository map
```
backend/    FastAPI app (app/core, models, schemas, services, api/v1/routes), alembic/, tests/
frontend/   React app (src/api, components, pages, lib, styles), e2e/ (Playwright)
docs/       product, design, architecture (+ADR), development, operations, quality
tasks/      MASTER_TASKS.md + one file per phase
scripts/    localdb.mjs (embedded PostgreSQL), check.ps1/check.sh, check-secrets.py, check_docs.py
```

## Commands (Windows paths; on macOS/Linux use `.venv/bin/python`)
| Purpose | Command (run from) |
|---------|--------------------|
| Start the local PostgreSQL 17 (:54329) | `npm run db:start` (root) — keep it running |
| Install backend deps | `py -3.13 -m venv .venv && .venv/Scripts/python -m pip install -r requirements-dev.txt` (backend) |
| Migrate | `.venv/Scripts/python -m alembic upgrade head` (backend) |
| Seed sample data | `.venv/Scripts/python -m app.cli seed` (backend) |
| Create the first admin | `.venv/Scripts/python -m app.cli create-admin --email … --name …` (backend) |
| Run the API | `.venv/Scripts/python -m uvicorn app.main:app --reload --port 8010` (backend) |
| Backend tests | `.venv/Scripts/python -m pytest -q` (backend; DB must be running) |
| Lint / types (backend) | `.venv/Scripts/python -m ruff check . && .venv/Scripts/python -m mypy app` |
| Export the API contract | `.venv/Scripts/python -m app.cli export-openapi` (backend) |
| Frontend dev | `npm run dev` (frontend) → http://localhost:5180 |
| Generate API types | `npm run gen:api` (frontend) |
| Frontend checks | `npm run typecheck && npm run lint && npm test` (frontend) |
| E2E | `npm run e2e` (frontend; backend running with the simulator) |
| Everything | `powershell -File scripts/check.ps1` (root) |
| Docs/skills consistency | `py -3.13 scripts/check_docs.py` (root) |

Environment notes: use `py -3.13` (the Python 3.12 install on this machine is broken). Docker is not
installed. Node 24, TypeScript pinned to 5.9.x, ESLint 10, React Router 8 (`react-router` + `react-router/dom`).
Dev ports: web **5180**, API **8010** (5173 and 8000 are used by other projects on this machine).

## Documentation index
* Status & plan: `PROJECT_STATUS.md`, `IMPLEMENTATION_PLAN.md`, `tasks/`, `CHANGELOG.md`
* Product: `docs/PRODUCT_REQUIREMENTS.md`, `USER_JOURNEYS.md`, `FEATURE_MATRIX.md`,
  `ACCEPTANCE_CRITERIA.md`, `ASSUMPTIONS_AND_DECISIONS.md`
* Architecture: `docs/architecture/` — SYSTEM_ARCHITECTURE, DATABASE_SCHEMA, ER_DIAGRAM,
  API_CONTRACT, AUTHENTICATION, PRICING_ENGINE, PAYMENT_FLOW, INVENTORY_AND_ORDERS,
  SECURITY_MODEL, ADR/
* Design: `docs/design/` — DESIGN_SYSTEM, COMPONENT_LIBRARY, RESPONSIVE_GUIDELINES, ACCESSIBILITY
* Development: `docs/development/` — LOCAL_SETUP, ENVIRONMENT_VARIABLES, DATABASE_MIGRATIONS,
  SEED_DATA, TESTING, CODE_CONVENTIONS, COMMON_ERRORS
* Operations: `docs/operations/` — DEPLOYMENT, BACKUP_AND_RESTORE, MONITORING, INCIDENT_RESPONSE,
  PRODUCTION_CHECKLIST, PAYMENT_PROVIDER_SETUP, EMAIL_SETUP, SHIPPING_SETUP
* Quality: `docs/quality/` — TEST_PLAN, TEST_RESULTS, SECURITY_REVIEW, PERFORMANCE_REVIEW,
  KNOWN_LIMITATIONS

## Workflow loop
INSPECT → PLAN → DOCUMENT → DESIGN → IMPLEMENT → TEST → REVIEW → UPDATE DOCS → CONTINUE.
At each verified checkpoint: update `PROJECT_STATUS.md`, tick tasks, add a TEST_RESULTS entry,
update CHANGELOG, and commit (feature branch, attribution lines per the session's instructions).
If context runs low: stop at a verified checkpoint and write "How to resume" in PROJECT_STATUS.md.
