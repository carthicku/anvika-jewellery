#!/usr/bin/env bash
# Runs every static check and automated test for both apps. Stops at the first failure.
# Usage (repository root, local DB running):  bash scripts/check.sh [--e2e]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "$ROOT/backend/.venv/Scripts/python.exe" ]]; then PY="$ROOT/backend/.venv/Scripts/python.exe"; else PY="$ROOT/backend/.venv/bin/python"; fi
if command -v py >/dev/null 2>&1; then SYS_PY="py -3.13"; else SYS_PY="python3"; fi

step() { printf '\n=== %s ===\n' "$1"; }

step "Docs & skills consistency"; $SYS_PY "$ROOT/scripts/check_docs.py"
step "Secret scan";               $SYS_PY "$ROOT/scripts/check-secrets.py"

cd "$ROOT/backend"
step "Backend: ruff lint";            "$PY" -m ruff check .
step "Backend: ruff format";          "$PY" -m ruff format --check .
step "Backend: mypy";                 "$PY" -m mypy app
step "Backend: migrations in sync";   "$PY" -m alembic check
step "Backend: pytest";               "$PY" -m pytest -q
step "Backend: OpenAPI export";       "$PY" -m app.cli export-openapi

cd "$ROOT/frontend"
step "Frontend: API types up to date"; npm run check:api --silent
step "Frontend: typecheck";            npm run typecheck --silent
step "Frontend: lint";                 npm run lint --silent
step "Frontend: format";               npm run format:check --silent
step "Frontend: unit tests";           npm test --silent
step "Frontend: production build";     npm run build --silent
if [[ "${1:-}" == "--e2e" ]]; then step "Frontend: end-to-end"; npm run e2e --silent; fi

printf '\nAll checks passed.\n'
