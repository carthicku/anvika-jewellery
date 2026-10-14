# Security Review

Threat model and intended controls: [SECURITY_MODEL.md](../architecture/SECURITY_MODEL.md).
This file records **reviews actually performed**, with findings and their resolution. A control is
only listed as verified when a test or an inspection proves it.

## Review log

### 2026-10-14 — Design review (Phase 0)
Scope: architecture documents only (no code yet).
| Finding | Severity | Resolution |
|---------|----------|-----------|
| Supabase's auto-generated Data API could expose tables if left enabled | High | ADR-0002: RLS enabled with no policies on all tables + disable the Data API (checklist item) |
| Gold accent colour (#B08D57) fails 3:1 as a focus indicator | Medium (a11y) | Separate `focus` token #9C7A45 (3.7:1) |
| Cross-site deployment would break SameSite cookies | Medium | Same-origin deployment mandated (ADR-0003, DEPLOYMENT.md) |

## Control verification status
| Control (SECURITY_MODEL #) | Status | Evidence |
|----------------------------|--------|----------|
| 1 Server-side pricing | ✅ cart (checkout pending) | `test_browser_supplied_prices_are_rejected` (unknown `unit_price` field → 422); cart responses always re-priced; component test asserts no price is sent |
| 2 Payment verification | ⬜ | |
| 3 Webhook HMAC + idempotency | ⬜ | |
| 4 Overselling protection | ⬜ | |
| 5 Duplicate orders | ⬜ | |
| 6 Brute-force protection | ✅ | Argon2id; `test_login_is_rate_limited_per_account`; per-IP limits on login/register/forgot/reset |
| 7 XSS / CSP | ⚠️ partial | Markdown rendered without raw HTML (react-markdown default); JSON-LD escapes `<`; CSP pending deploy config |
| 8 CSRF | ✅ middleware verified | `test_foundation.py` CSRF tests (missing/mismatched/foreign origin/webhook exemption) |
| 9 Refresh rotation | ✅ | `test_refresh_rotates_and_detects_reuse`, `test_concurrent_refresh_from_two_tabs_is_not_treated_as_theft` |
| 10 IDOR | ✅ accounts (orders pending) | `test_customers_cannot_touch_each_others_addresses`, `test_wishlists_are_private`, session revoke scoped to owner |
| 11 Admin RBAC | ⚠️ guard in place, admin routes pending | `test_every_admin_route_declares_a_permission`, `test_guard_detects_an_unprotected_admin_route`, role taken from DB row |
| 12 Enumeration | ✅ login + reset (registration reveals by design) | `test_login_success_and_wrong_password_are_distinct`, `test_forgot_password_never_reveals_accounts` |
| 13 SQL injection | ✅ catalogue search | parameterised queries only; `test_search_handles_hostile_input` (quotes, `%`, `_`, backslash, emoji, SQL fragments) |
| 14 Uploads | ⬜ | |
| 15 Secrets | ⚠️ scanner + production config validation verified; log redaction untested | `scripts/check-secrets.py`, `test_settings.py` |
| 16 Error leakage | ✅ | `test_app_errors_and_unexpected_errors_are_formatted` (no internal detail in 500) |
| 17 Spam | ✅ contact + newsletter | honeypot, minimum fill time, rate limits: `test_contact_spam_is_silently_dropped`, `test_contact_is_rate_limited` |
| 18 Security headers | ⚠️ API headers verified; SPA CSP/HSTS pending deploy config | `test_security_headers_present` |
| 19 CORS | ⬜ | |
| 20 Guest order access | ⬜ | |
| 21 Admin money safeguards | ⬜ | |
| 22 Supabase RLS | ✅ RLS on every table (local) | `test_every_application_table_has_row_level_security`; disabling the Data API is a deployment step |
| 23 Dependency audit | ⬜ | |

### 2026-10-14 — Authentication review (Phase 4)
Scope: `app/core/security.py`, `app/services/auth.py`, `app/api/deps.py`, auth/account routes, cookies.
| Finding | Severity | Resolution |
|---------|----------|-----------|
| Refresh reuse detection would sign out users with two tabs refreshing simultaneously | Low (availability) | 20-second race window returns `409 REFRESH_RACE` without revocation |
| Revocation after token reuse could be rolled back by the failing request | Medium | Service commits the revocation before raising |
| Clearing cookies on failed refresh used a hand-written Set-Cookie without Secure/SameSite | Low | Uses the shared cookie helper |
| One-time links persisted in the email outbox after sending | Medium | Context cleared once sent |
| Open redirect via `?next=` | Medium | `safeNext` allows same-site paths only (unit-tested) |
| JWT algorithm confusion | — | Decoder pins `HS256` and requires exp/iat/sub/sid/typ |
Not yet done: admin MFA (Phase 7), breached-password screening (not planned; documented in KNOWN_LIMITATIONS).
