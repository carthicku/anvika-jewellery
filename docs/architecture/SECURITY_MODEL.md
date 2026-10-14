# Security Model

This document lists what we protect, who might attack it, and the control for each threat. Review
results are recorded in [`docs/quality/SECURITY_REVIEW.md`](../quality/SECURITY_REVIEW.md).

## 1. Assets
Customer personal data (names, emails, phones, addresses), account credentials, order and payment
records, the store's money (prices, coupons, refunds), inventory of high-value items, admin
access, and secrets (JWT key, Razorpay keys, SMTP and DB passwords).

## 2. Threats and controls

| # | Threat | Control | Where |
|---|--------|---------|-------|
| 1 | Price/total tampering from the browser | Prices recalculated server-side; browser `expected_total` used only as a consent check; Razorpay amount from DB | `services/pricing.py`, `services/checkout.py` |
| 2 | Fake payment success (forged redirect/callback) | HMAC signature with server-stored order id + payment fetched from Razorpay + amount/currency/status checks | `services/payments/` |
| 3 | Forged or replayed webhooks | HMAC over raw body; unique `event_id`; idempotent processing | `routes/webhooks.py` |
| 4 | Overselling / race conditions | Row locks, CHECK constraints, single transaction | `services/inventory.py` |
| 5 | Duplicate orders | `Idempotency-Key` unique; reuse of pending order | `services/checkout.py` |
| 6 | Account takeover by password guessing | Argon2id, rate limits per IP and per email, generic errors | `services/auth.py`, `core/rate_limit.py` |
| 7 | Session theft via XSS | HttpOnly cookies, CSP, React escaping, no `dangerouslySetInnerHTML` with untrusted data, markdown rendered without raw HTML | frontend, `core/security_headers.py` |
| 8 | CSRF | Double-submit token + Origin check + SameSite cookies | `core/csrf.py` |
| 9 | Refresh-token theft | Rotation with reuse detection; hash-only storage | `services/auth.py` |
| 10 | Broken access control (IDOR) | Ownership filters in every customer query; 404 for others' data; tests for each resource | services + `tests/api/test_access_control.py` |
| 11 | Privilege escalation to admin | Role from DB, fixed permission map, `require_permission` on every admin route (test enforces), role changes admin-only and audited | `core/permissions.py`, `api/deps.py` |
| 12 | Account enumeration | Forgot-password always 202; login generic message; registration says "check your email / sign in" without confirming existence where possible | `services/auth.py` |
| 13 | SQL injection | SQLAlchemy parameterised queries only; no string-built SQL; search uses `websearch_to_tsquery` with bound parameters | everywhere |
| 14 | Malicious uploads | Admin-only; 10 MB limit; Pillow decodes and re-encodes to WebP (drops scripts/metadata); random file names; allow-list of formats; never served from user-chosen paths | `services/storage.py`, `services/images.py` |
| 15 | Secrets leakage | Env vars only; `.env` git-ignored; `SecretStr` in settings; logs redact `password`, `token`, `secret`, `authorization`, `cookie`; no `VITE_` secrets | `core/config.py`, `core/logging.py` |
| 16 | Information leakage in errors | Generic 500 with `request_id`; stack traces only in logs; OpenAPI docs disabled in production | `core/errors.py` |
| 17 | Spam / abuse of forms | Rate limits, honeypot field, length limits, minimum fill time on contact/newsletter forms | `routes/content.py` |
| 18 | Clickjacking, MIME sniffing, etc. | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, HSTS in production, CSP | `core/security_headers.py` + hosting config |
| 19 | Over-permissive CORS | Same-origin by default; `ALLOWED_ORIGINS` explicit list; credentials only for listed origins | `main.py` |
| 20 | Guest order snooping | Order reference alone reveals nothing; guest access needs a 256-bit token sent only to the purchaser | `services/orders.py` |
| 21 | Admin mistakes on money | Rate change preview + large-change confirmation; admins cannot set `paid`; refunds need `orders:refund`; every sensitive action audited | admin services |
| 22 | Direct DB access through Supabase APIs | RLS enabled with no policies on all tables; Data API disabled; anon key unused | DEPLOYMENT.md |
| 23 | Dependency vulnerabilities | `pip-audit` and `npm audit` in the release checklist; lockfiles committed | PRODUCTION_CHECKLIST.md |

## 3. Content Security Policy (production)
```
default-src 'self';
script-src 'self' https://checkout.razorpay.com;
frame-src https://api.razorpay.com https://checkout.razorpay.com;
connect-src 'self' https://lumberjack.razorpay.com;
img-src 'self' data: https:;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
frame-ancestors 'none'; base-uri 'self'; form-action 'self'
```
Razorpay host names must be re-checked against Razorpay's current documentation when the CSP is
deployed (listed as an item in the production checklist).

## 4. Logging and privacy
* Structured JSON logs with `request_id`, method, path, status, duration, and user id (not email).
* Never logged: passwords, tokens, cookies, `Authorization` headers, full addresses, card or UPI
  details, Razorpay secrets.
* IP addresses are stored on sessions and audit logs for security only. Retention guidance is in
  [`BACKUP_AND_RESTORE.md`](../operations/BACKUP_AND_RESTORE.md#data-retention).

## 5. Known gaps (also in KNOWN_LIMITATIONS)
* Admin MFA is planned (Phase 7), not yet implemented.
* No WAF / bot management. Use the hosting provider's protection at launch.
* No automated malware scanning of uploads beyond image re-encoding.
