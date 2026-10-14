# Common Errors and Fixes

Add an entry whenever you solve a confusing problem.

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Python was not found; run without arguments to install from the Microsoft Store` | Windows `python` alias points to the Store | Use `py -3.13` to create the venv, then always use `.venv/Scripts/python`. |
| `Unable to create process using '...Python312\python.exe'` | A broken Python 3.12 registration on this machine | Use `py -3.13`. |
| `connection refused` on port 54329 | Local database not running | Run `npm run db:start` in its own terminal. |
| `EPERM ... rmdir` from embedded-postgres | Windows file lock when the server stops with non-persistent data | The launcher uses `persistent: true`; if it happens, close terminals holding `.localdb/` and retry. |
| `database "anvika_dev" does not exist` | DB server started outside our script | Run `npm run db:start` once (it creates the databases). |
| `alembic: command not found` | venv not active | Use `.venv/Scripts/python -m alembic ...`. |
| `Target database is not up to date` | Unapplied migrations | `python -m alembic upgrade head`. |
| `403 CSRF_FAILED` in the browser | `csrf_token` cookie missing or header not sent | The API client calls `/auth/csrf` automatically; clear cookies and reload. In tests, use the `client` fixture, which handles CSRF. |
| Logged out immediately on `http://` in production | `COOKIE_SECURE=true` requires HTTPS | Serve over HTTPS (always in production). Locally use `http://localhost`, where `COOKIE_SECURE=false`. |
| Cookies not set when the frontend and API are on different domains | `SameSite` rules | Serve the API on the same origin (reverse proxy) or the same registrable domain — see ADR-0003. |
| `PAYMENT_PROVIDER=simulator is not allowed in production` at start-up | Safety check working as intended | Configure Razorpay keys and set `PAYMENT_PROVIDER=razorpay`. |
| Razorpay pop-up opens but verification fails with `PAYMENT_SIGNATURE_INVALID` | Wrong `RAZORPAY_KEY_SECRET` (e.g. live secret with test key id) | Use the matching test key id and secret pair. |
| Webhook returns 400 | Wrong webhook secret, or a proxy modified the body | Check `RAZORPAY_WEBHOOK_SECRET`; make sure nothing re-encodes the JSON body. |
| Frontend type errors after a backend change | Stale `schema.d.ts` | Regenerate API types (see LOCAL_SETUP §7). |
| `npm ERR! peer dep` with TypeScript 7 | typescript-eslint supports TS < 6.1 | Keep `typescript` pinned to `~6.0`. |
| Playwright: `Executable doesn't exist` | Browsers not installed | `npx playwright install chromium`. |
