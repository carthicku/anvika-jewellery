# Runs every static check and automated test for both apps. Stops at the first failure.
# Usage (repository root, with the local DB running via `npm run db:start`):
#   powershell -ExecutionPolicy Bypass -File scripts/check.ps1
# Skip end-to-end tests by default; add -E2E to include them (needs the backend running).
param([switch]$E2E)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root 'backend\.venv\Scripts\python.exe'

function Step($name, [scriptblock]$action) {
  Write-Host "`n=== $name ===" -ForegroundColor Cyan
  & $action
  if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $name" -ForegroundColor Red; exit $LASTEXITCODE }
}

Step 'Docs & skills consistency' { py -3.13 (Join-Path $root 'scripts\check_docs.py') }
Step 'Secret scan' { py -3.13 (Join-Path $root 'scripts\check-secrets.py') }

Push-Location (Join-Path $root 'backend')
try {
  Step 'Backend: ruff lint' { & $py -m ruff check . }
  Step 'Backend: ruff format' { & $py -m ruff format --check . }
  Step 'Backend: mypy' { & $py -m mypy app }
  Step 'Backend: migrations in sync' { & $py -m alembic check }
  Step 'Backend: pytest' { & $py -m pytest -q }
  Step 'Backend: OpenAPI export' { & $py -m app.cli export-openapi }
} finally { Pop-Location }

Push-Location (Join-Path $root 'frontend')
try {
  Step 'Frontend: API types up to date' { npm run check:api --silent }
  Step 'Frontend: typecheck' { npm run typecheck --silent }
  Step 'Frontend: lint' { npm run lint --silent }
  Step 'Frontend: format' { npm run format:check --silent }
  Step 'Frontend: unit tests' { npm test --silent }
  Step 'Frontend: production build' { npm run build --silent }
  if ($E2E) { Step 'Frontend: end-to-end' { npm run e2e --silent } }
} finally { Pop-Location }

Write-Host "`nAll checks passed." -ForegroundColor Green
