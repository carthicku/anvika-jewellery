# Common Errors and Fixes

Add an entry whenever you solve a confusing problem.

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Python was not found; run without arguments to install from the Microsoft Store` | Windows `python` alias points to the Store | Use `py -3.13` to create the venv, then always use `.venv/Scripts/python`. |
| `Unable to create process using '...Python312\python.exe'` | A broken Python 3.12 registration on this machine | Use `py -3.13`. |
| `UnicodeEncodeError: 'charmap' codec can't encode character` when saving data | The local cluster was initialised as WIN1252 (Windows default) | `scripts/localdb.mjs` now initialises UTF-8 and refuses non-UTF-8 clusters. Stop the DB, delete `.localdb/` (local dev data only) and run `npm run db:start`. |
| `connection refused` on port 54329 | Local database not running | Run `npm run db:start` in its own terminal. |
| `EPERM ... rmdir` from embedded-postgres | Windows file lock when the server stops with non-persistent data | The launcher uses `persistent: true`; if it happens, close terminals holding `.localdb/` and retry. |
| `database "anvika_dev" does not exist` | DB server started outside our script | Run `npm run db:start` once (it creates the databases). |
| `alembic: command not found` | venv not active | Use `.venv/Scripts/python -m alembic ...`. |
| `Target database is not up to date` | Unapplied migrations | `python -m alembic upgrade head`. |
| `403 CSRF_FAILED` in the browser | `csrf_token` cookie missing or header not sent | The API client calls `/auth/csrf` automatically; clear cookies and reload. In tests, use the `client` fixture, which handles CSRF. |
| Logged out immediately on `http://` in production | `COOKIE_SECURE=true` requires HTTPS | Serve over HTTPS (always in production). Locally use `http://localhost`, where `COOKIE_SECURE=false`. |
| Cookies not set when the frontend and API are on different domains | `SameSite` rules | Serve the API on the same origin (reverse proxy) or the same registrable domain — see ADR-0003. |
| `PAYMENT_PROVIDER=simulator is not allowed in production` at start-up | Safety check working as intended | Configure Razorpay keys and set `PAYMENT_PROVIDER=razorpay`. |
| Razorpay pop-up opens but verification fails with `PAYMENT_VERIFICATION_FAILED` | Wrong `RAZORPAY_KEY_SECRET` (e.g. live secret with test key id) | Use the matching test key id and secret pair. |
| Webhook returns 400 | Wrong webhook secret, or a proxy modified the body | Check `RAZORPAY_WEBHOOK_SECRET`; make sure nothing re-encodes the JSON body. |
| Frontend type errors after a backend change | Stale `schema.d.ts` | Regenerate API types (see LOCAL_SETUP §7). |
| `npm ERR! peer dep` mentioning `typescript` | `openapi-typescript` 7.x requires TypeScript 5; typescript-eslint requires < 6.1 | Keep `typescript` pinned to `~5.9`. |
| `[Errno 10048] error while attempting to bind on address (127.0.0.1, 8010)` | Another program already uses the port | Run uvicorn with another `--port` and set `VITE_API_PROXY_TARGET` in `frontend/.env` to match. (This project defaults to 8010 because 8000 was taken on the development machine.) |
| Playwright: `Executable doesn't exist` | Browsers not installed | `npx playwright install chromium`. |
| New API routes return 404 / missing from `/api/docs` while developing | The `--reload` worker stopped reloading (e.g. it reloaded while a file was half-written) | Stop uvicorn (Ctrl+C) and start it again. |
| Simulated payment "can't be verified" after restarting the API | The default `SIMULATOR_SECRET` is random per process | Start a new payment (Try payment again), or set a fixed `SIMULATOR_SECRET` in `backend/.env` for development. |
