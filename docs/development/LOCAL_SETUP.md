# Local Setup (Windows, macOS, Linux)

This guide assumes no prior experience. Commands are shown for **Git Bash / PowerShell on
Windows**. macOS/Linux differences are noted.

## 1. Install the tools (once)
| Tool | Version used | Check with |
|------|--------------|-----------|
| Node.js | 24.x (≥ 22.22 required by React Router 8) | `node --version` |
| npm | 11.x | `npm --version` |
| Python | 3.13 (3.11+ works) | `py -3.13 --version` (Windows) / `python3 --version` |
| Git | any recent | `git --version` |

Docker is **optional**. Without it, we run PostgreSQL through the `embedded-postgres` npm package.

## 2. Get the code and install dependencies
```bash
# from the project root
npm install                      # root tools: the embedded PostgreSQL launcher

cd backend
py -3.13 -m venv .venv           # macOS/Linux: python3 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # macOS/Linux: .venv/bin/python
cp .env.example .env             # then open .env and set SECRET_KEY (see below)
cd ..

cd frontend
npm install
cp .env.example .env
cd ..
```
Generate a `SECRET_KEY`:
```bash
backend/.venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> **What is a virtual environment (`.venv`)?** A private folder of Python packages for this project,
> so they don't clash with other projects. Always use `.venv/Scripts/python` (Windows) or
> `.venv/bin/python` (macOS/Linux), or "activate" it first: `source .venv/Scripts/activate`.

## 3. Start the database (terminal 1 — leave it running)
```bash
npm run db:start
```
This starts PostgreSQL 17 on `127.0.0.1:54329` (data kept in `.localdb/`) and creates the
`anvika_dev` and `anvika_test` databases. Stop it with `Ctrl+C`.

*With Docker instead:* `docker compose up -d db` (same port and credentials).

## 4. Create tables and sample data (once, and after pulling new migrations)
```bash
cd backend
.venv/Scripts/python -m alembic upgrade head     # applies migrations (creates/updates tables)
.venv/Scripts/python -m app.cli seed             # adds sample catalogue, rates, shipping, pages
.venv/Scripts/python -m app.cli create-admin --email you@example.com --name "Your Name"
```

## 5. Run the backend (terminal 2)
```bash
cd backend
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8010
```
* Health check: http://127.0.0.1:8010/api/v1/health
* API docs (development only): http://127.0.0.1:8010/api/docs

## 6. Run the frontend (terminal 3)
```bash
cd frontend
npm run dev
```
Open http://localhost:5180. The Vite dev server forwards `/api/*` and `/media/*` to the backend, so
cookies work without CORS.

## 7. Everyday commands
| Task | Command |
|------|---------|
| All checks (lint, types, tests) | `powershell -File scripts/check.ps1` or `bash scripts/check.sh` |
| Backend tests | `cd backend && .venv/Scripts/python -m pytest` |
| Frontend unit tests | `cd frontend && npm test` |
| End-to-end tests | `cd frontend && npx playwright install chromium` (once), then `npm run e2e` |
| Regenerate API types | `cd backend && .venv/Scripts/python -m app.cli export-openapi && cd ../frontend && npm run gen:api` |
| Read development emails | open the `.eml` files in `backend/var/mail/` |
| Process background jobs now | `cd backend && .venv/Scripts/python -m app.cli run-jobs` |

Problems? See [COMMON_ERRORS.md](COMMON_ERRORS.md).
