# Code Conventions

## General
* Prefer clear, boring code over clever code. A beginner should be able to follow any function.
* Comments explain **why**, not what. Business rules link to the doc that defines them
  (e.g. `# See docs/architecture/PRICING_ENGINE.md §3`).
* No unfinished `TODO`s in auth, checkout, payments, inventory or pricing. Elsewhere, write
  `TODO(phase-N): …` and add the item to the matching `tasks/PHASE_0N_*.md`.
* Do not add a dependency without stating why in the commit message. Prefer the standard library.

## Python (backend)
| Topic | Rule |
|-------|------|
| Formatting / lint | `ruff format` + `ruff check` (config in `pyproject.toml`, line length 100) |
| Types | Type hints everywhere; `mypy app` must pass (strict-ish settings in `pyproject.toml`) |
| Naming | `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` constants; modules are domain nouns (`orders.py`) |
| Layers | `routes/` → `services/` → `models/`. Routes never import other routes. Services may call other services. Models contain no business logic beyond simple properties. |
| Transactions | A service function that changes data receives a `Session`, does its work, and lets the route's unit of work commit (`db.commit()` in the route after the service returns, or `with db.begin():` inside multi-step services). Never commit in the middle of a business operation. |
| Errors | Raise subclasses of `app.core.errors.AppError` (`NotFound`, `Conflict`, `Forbidden`, `BadRequest`, `ValidationFailed`, `OutOfStock`, `PriceChanged`, …). Never raise `HTTPException` from services. |
| Money | `Decimal` only. Never `float`. Use `app.core.money.money()` to round. Serialise as strings (`MoneyStr` Pydantic type). |
| Time | `datetime.now(UTC)` via `app.core.time.utcnow()`; columns are `timestamptz`. |
| Schemas | Request models end with `In` (e.g. `AddressIn`), response models with `Out`. Use `model_config = ConfigDict(extra="forbid")` on inputs so unknown fields are rejected. |
| Queries | SQLAlchemy 2.x `select()` style. Never build SQL with f-strings. Use `selectinload` to avoid N+1 queries on lists. |
| Tests | `tests/unit` (no DB), `tests/api` (TestClient + real PostgreSQL test DB, each test in a rolled-back transaction where possible). Test names describe behaviour: `test_customer_cannot_view_other_customers_order`. |

## TypeScript / React (frontend)
| Topic | Rule |
|-------|------|
| Formatting / lint | Prettier + ESLint (typescript-eslint strict, react-hooks, jsx-a11y) |
| Types | `strict: true`, `noUncheckedIndexedAccess: true`. No `any` (use `unknown` and narrow). API types come from `src/api/schema.d.ts` (generated — never edit by hand). |
| Files | Components `PascalCase.tsx`, hooks `useThing.ts`, utilities `camelCase.ts`. One exported component per file (small private helpers allowed). |
| Imports | Use the `@/` alias for `src/`. |
| Data | Server data only via TanStack Query hooks in `src/api/queries/*`. Query keys are defined in `src/api/queryKeys.ts`. |
| Business logic | **None.** No price, tax, discount or stock arithmetic in the frontend. Format and display only. |
| Forms | React Hook Form + Zod schema in `src/lib/validation/`. The backend repeats every validation. |
| Styling | Tailwind utilities with design tokens; `cn()` to merge classes; no inline hex colours; no `!important`. |
| Accessibility | Use semantic elements first; Radix for complex widgets; every icon-only button has `aria-label`. |
| States | Every data view renders loading (skeleton), error (`ErrorState` with retry), empty (`EmptyState`) and success. |
| Tests | Vitest + Testing Library, querying by role/label text, not by CSS classes. |
| Links | Use `<Link>` for internal navigation. Never `href="#"`. Buttons that navigate are links; links that act are buttons. |

## Git
* Branches: `main` (always deployable), feature branches `feat/<short-name>`, fixes `fix/<name>`.
* Commits: imperative mood, ≤ 72-character subject (`Add gold rate preview endpoint`), body explains
  why. Commit lockfiles (`package-lock.json`, `backend/requirements*.txt`).
* Never commit `.env` files, database dumps, or files from `backend/var/`.
* Before pushing: run `scripts/check.ps1` (or `scripts/check.sh`), which runs lint, type checks
  and tests for both apps.

## Database
* Every schema change is an Alembic migration (`alembic revision --autogenerate -m "..."`), reviewed by
  hand before committing (autogenerate misses some things: CHECK constraints, server defaults,
  generated columns).
* Migrations must be safe to run on production: add columns as nullable or with defaults, backfill,
  then tighten. Never drop columns with data in the same release that stops using them.
