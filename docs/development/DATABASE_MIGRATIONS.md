# Database Migrations (Alembic)

A **migration** is a small Python file that changes the database structure (add a table, add a
column…) in a repeatable, version-controlled way. Alembic remembers which migrations have been
applied in the `alembic_version` table.

All commands run inside `backend/` with the virtual environment's Python.

| Task | Command |
|------|---------|
| Apply all pending migrations | `.venv/Scripts/python -m alembic upgrade head` |
| See the current version | `.venv/Scripts/python -m alembic current` |
| See history | `.venv/Scripts/python -m alembic history --verbose` |
| Create a migration after changing models | `.venv/Scripts/python -m alembic revision --autogenerate -m "add gift message to orders"` |
| Check models and migrations agree | `.venv/Scripts/python -m alembic check` |
| Undo the last migration (**development only**) | `.venv/Scripts/python -m alembic downgrade -1` |

## Workflow for a schema change
1. Edit the SQLAlchemy model in `app/models/`.
2. Autogenerate a migration, then **read it**. Autogenerate does not reliably detect: CHECK
   constraints, generated columns (`search_vector`), server defaults, partial indexes, enum value
   changes. Add these by hand.
3. Apply it to your dev DB: `alembic upgrade head`.
4. Run the tests (the test suite builds the test DB by running all migrations from scratch, which
   proves the chain works on an empty database).
5. Run `alembic check` — it must report no differences.
6. Commit the model change and the migration together.

## Production rules
* Back up first (see [BACKUP_AND_RESTORE.md](../operations/BACKUP_AND_RESTORE.md)).
* Run `alembic upgrade head` as a separate release step **before** starting the new app version.
* Use expand → migrate → contract for risky changes: add the new nullable column, deploy code that
  writes both, backfill, then make it required in a later release.
* Never run `downgrade` against production unless the migration was written to be reversible and
  you have a backup.
* Never "reset" the production database. `scripts/` contains no command that drops a production
  database. The test fixture that recreates the schema refuses to run unless the database name ends
  in `_test`.

## Supabase specifics
* Use the session pooler connection string (port 5432) for migrations.
* The first migration enables Row Level Security on every application table (with no policies), so
  Supabase's auto-generated Data API cannot read them even if it is accidentally enabled. Our backend
  connects as the `postgres` role (table owner), which bypasses RLS, so our queries are unaffected.
