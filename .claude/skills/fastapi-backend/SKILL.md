---
name: fastapi-backend
description: Use when writing or reviewing code in backend/ (FastAPI, Pydantic v2, SQLAlchemy 2.x sync, Alembic, psycopg 3) — routers, schemas, services, models, dependencies, error handling, migrations and API tests.
---

# FastAPI backend conventions

## Shape of a feature
1. **Model** (`app/models/<domain>.py`): `Mapped[...]` typed columns; money `Numeric(12, 2)`, weights
   `Numeric(10, 3)`; enum-like strings with a `CheckConstraint`; timestamps `DateTime(timezone=True)`.
2. **Migration**: `alembic revision --autogenerate -m "..."`, then hand-check CHECK constraints,
   server defaults, generated columns, partial indexes, and the `ENABLE ROW LEVEL SECURITY` statement
   for new tables.
3. **Schemas** (`app/schemas/<domain>.py`): inputs `…In` with `extra="forbid"` and explicit length
   limits; outputs `…Out` with `from_attributes=True`; money as `MoneyStr`.
4. **Service** (`app/services/<domain>.py`): plain functions taking `db: Session` and typed args;
   enforce ownership (`user_id == current_user.id`); raise `AppError` subclasses; lock rows
   (`with_for_update()`) for stock/order/payment changes.
5. **Route** (`app/api/v1/routes/<domain>.py`): `def` handlers (sync); dependencies
   `db=Depends(get_db)`, `user=Depends(get_current_user)` or `Depends(require_permission("x:y"))`;
   call one service; `db.commit()`; return the schema. Declare `response_model` and `status_code`.
6. **Tests** (`tests/api/test_<domain>.py`): happy path, validation error, unauthenticated,
   wrong user (404), wrong role (403), plus domain edge cases.

## Non-negotiables
* Never trust client-sent prices, totals, roles, stock or payment status.
* Every `/api/v1/admin/*` route has `require_permission(...)` (a test enforces this).
* Unsafe methods require CSRF (middleware). Only webhooks are exempt.
* No `float` for money. No f-string SQL. No secrets in logs (`app/core/logging.py` redacts them).
* Consistent errors: `{"error": {"code", "message", "details", "request_id"}}`. Use 404 for other
  people's resources.
* List endpoints are paginated (`page`, `page_size` with max).
* Idempotency for anything that must not happen twice (orders, payments, emails).
* Sensitive endpoints are rate-limited with `rate_limit(...)`.

## Commands (run inside backend/)
```
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check . && .venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m mypy app
.venv/Scripts/python -m alembic upgrade head && .venv/Scripts/python -m alembic check
.venv/Scripts/python -m app.cli export-openapi
```
