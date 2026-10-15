# Environment Variables

* Backend variables are read by `backend/app/core/config.py` (pydantic-settings) from the process
  environment and from `backend/.env` (development only). Copy `backend/.env.example` to
  `backend/.env` and fill in values.
* Frontend variables are read by Vite at **build time** from `frontend/.env`. Anything starting with
  `VITE_` ends up in the public JavaScript bundle, so **never put a secret in a `VITE_` variable.**
* Production values are set in the hosting provider's secret manager, never in files committed to
  Git.
* The app refuses to start in `production` if a required secret is missing, still has its example
  value, or is too short.

## Backend

| Variable | Required | Default (dev) | Description |
|----------|:-:|---------------|-------------|
| `APP_ENV` | ✅ | `development` | `development`, `test` or `production`. Production enables strict checks (Secure cookies, no API docs, no simulator). |
| `SECRET_KEY` | ✅ | — | ≥ 32 random characters. Signs JWTs. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Rotating it signs everyone out. |
| `DATABASE_URL` | ✅ | `postgresql+psycopg://postgres:postgres@127.0.0.1:54329/anvika_dev` | SQLAlchemy URL. For Supabase use the **session pooler** URI with the `postgresql+psycopg://` prefix and `?sslmode=require`. |
| `TEST_DATABASE_URL` | tests | `postgresql+psycopg://postgres:postgres@127.0.0.1:54329/anvika_test` | Used by pytest only. **Its data is wiped by the test suite.** |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | | `5` / `5` | Connection pool sizing. Keep the total under the Supabase plan's connection limit. |
| `PUBLIC_SITE_URL` | ✅ prod | `http://localhost:5180` | Canonical storefront URL used in emails, sitemap and links. |
| `ALLOW_SEARCH_INDEXING` | | `false` | `true` only on the live site: `/robots.txt` then allows crawling (private areas stay disallowed) and lists the sitemap. When `false` it disallows everything, so staging copies never show up in search results. |
| `ALLOWED_ORIGINS` | ✅ prod | `http://localhost:5180` | Comma-separated origins allowed for CORS and the CSRF Origin check. |
| `COOKIE_SECURE` | | `false` (dev), forced `true` in prod | Adds the `Secure` flag to cookies. |
| `COOKIE_DOMAIN` | | empty | Set to `.example.in` only if the API runs on a subdomain. |
| `TRUSTED_PROXY_COUNT` | | `0` | Number of reverse proxies in front of the app; used to read the client IP from `X-Forwarded-For` safely. |
| `ACCESS_TOKEN_TTL_MINUTES` | | `15` | Access JWT lifetime. |
| `REFRESH_TOKEN_TTL_DAYS` | | `30` | Refresh token lifetime. |
| `EMAIL_VERIFICATION_REQUIRED` | | `false` | If `true`, unverified accounts see a verification banner and cannot write reviews. |
| `STORE_NAME` | | `Anvika` | Brand name in emails and page titles (placeholder — see ASSUMPTIONS B1). |
| `ORDER_REFERENCE_PREFIX` | | `ANV` | Prefix of order references. |
| `PAYMENT_PROVIDER` | ✅ | `simulator` | `razorpay` or `simulator` (**simulator is rejected when `APP_ENV=production`**). |
| `RAZORPAY_KEY_ID` | when razorpay | — | Public key id (`rzp_test_…` / `rzp_live_…`). Sent to the browser by the API. |
| `RAZORPAY_KEY_SECRET` | when razorpay | — | **Secret.** Backend only. |
| `RAZORPAY_WEBHOOK_SECRET` | when razorpay | — | **Secret.** Set the same value in the Razorpay dashboard webhook settings. |
| `RAZORPAY_API_BASE` | | `https://api.razorpay.com/v1` | Override only for tests. |
| `SIMULATOR_SECRET` | dev/test | random at start-up | Signs simulated payments. |
| `PAYMENT_WINDOW_MINUTES` | | `30` | How long a pending order holds stock. |
| `EMAIL_BACKEND` | | `file` | `file` (writes `.eml` files to `EMAIL_FILE_DIR`), `console`, `smtp`, or `memory` (tests). |
| `EMAIL_FROM` | ✅ prod | `"Anvika <no-reply@example.com>"` | Sender address (must be verified with your provider). |
| `EMAIL_FILE_DIR` | | `var/mail` | Development email sink folder (relative to `backend/`). |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS` | when smtp | —, `587`, —, —, `true` | SMTP credentials (**password is secret**). |
| `STORAGE_BACKEND` | | `local` | `local` (files in `MEDIA_ROOT`, served at `/media`) or `s3` (S3-compatible, e.g. Supabase Storage, Cloudflare R2, AWS S3). |
| `MEDIA_ROOT` | | `var/media` | Local upload folder. |
| `S3_ENDPOINT_URL`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_PUBLIC_BASE_URL` | when s3 | — | Object storage settings (**keys are secret**). |
| `BACKGROUND_JOBS_ENABLED` | | `true` | Runs the in-process job loop (order expiry, email dispatch, price cache). Set `false` in tests and if you run `python -m app.cli run-jobs` from a scheduler instead. |
| `RATE_LIMIT_ENABLED` | | `true` | Disable only in specific tests. |
| `LOG_LEVEL` | | `INFO` | Python logging level. |
| `LOG_FORMAT` | | `text` (dev) / `json` (prod) | Log output format. |
| `MFA_ENCRYPTION_KEY` | Phase 7 | — | Fernet key for encrypting TOTP secrets. |

Store-level business settings (tax rates, announcement text, contact placeholders, rate-staleness
hours, large-change threshold) are **not** environment variables. They are stored in the
`store_settings` table and edited in **Admin → Settings**, because the owner changes them without a
deploy.

## Frontend (`frontend/.env`) — all public

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_STORE_NAME` | `Anvika` | Brand name used before `/settings/public` loads (header, titles). |
| `VITE_SITE_URL` | `http://localhost:5180` | Canonical URL base for `<link rel="canonical">` and Open Graph. |
| `VITE_API_ORIGIN` | empty | Origin of the API (e.g. `https://api.example.in`). Leave empty so requests go to the same origin (`/api/v1/...`), which is the recommended deployment. |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8010` | Dev server only: where Vite proxies `/api`, `/media` and `/sitemap.xml`. |

The Razorpay **key id** is not configured in the frontend. The backend returns it with each payment
request, so test and live keys are switched in one place.
