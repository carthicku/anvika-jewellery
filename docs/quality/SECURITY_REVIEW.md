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
| 1 Server-side pricing | ✅ | cart: `test_browser_supplied_prices_are_rejected`; checkout: `test_browser_cannot_send_prices`, `test_total_mismatch_is_refused_with_the_new_total`; Razorpay amount = stored `grand_total` in paise; `checkout.test.tsx` asserts the exact request body |
| 2 Payment verification | ✅ (mocked Razorpay) | `test_forged_signature_is_rejected`, `test_signature_is_checked_against_the_stored_provider_order`, `test_payment_for_another_order_cannot_pay_this_one`, `test_amount_mismatch_never_marks_paid`, `test_guest_cannot_verify_without_the_order_token` |
| 3 Webhook HMAC + idempotency | ✅ | `test_webhook_with_bad_signature_is_rejected_and_not_stored`, `test_webhook_capture_confirms_once_and_ignores_duplicates`, `test_webhook_with_wrong_amount_is_recorded_but_not_applied`, `test_webhook_signature_helper` |
| 4 Overselling protection | ✅ | `test_only_one_of_two_simultaneous_checkouts_gets_the_last_piece` (two real connections), `test_last_piece_goes_to_the_first_buyer`, DB CHECK `reserved <= on_hand` |
| 5 Duplicate orders | ✅ | `test_same_idempotency_key_returns_the_same_order`, `test_unchanged_cart_reuses_the_pending_order`, `test_idempotency_key_cannot_be_replayed_by_another_cart`, `test_verifying_twice_is_harmless`, frontend reuses the key for identical retries |
| 6 Brute-force protection | ✅ | Argon2id; `test_login_is_rate_limited_per_account`; per-IP limits on login/register/forgot/reset |
| 7 XSS / CSP | ⚠️ partial | Markdown rendered without raw HTML (react-markdown default); JSON-LD escapes `<`; CSP pending deploy config |
| 8 CSRF | ✅ middleware verified | `test_foundation.py` CSRF tests (missing/mismatched/foreign origin/webhook exemption) |
| 9 Refresh rotation | ✅ | `test_refresh_rotates_and_detects_reuse`, `test_concurrent_refresh_from_two_tabs_is_not_treated_as_theft` |
| 10 IDOR | ✅ accounts and orders | `test_customers_cannot_touch_each_others_addresses`, `test_wishlists_are_private`, session revoke scoped to owner |
| 11 Admin RBAC | ⚠️ guard in place, admin routes pending | `test_every_admin_route_declares_a_permission`, `test_guard_detects_an_unprotected_admin_route`, role taken from DB row |
| 12 Enumeration | ✅ login + reset (registration reveals by design) | `test_login_success_and_wrong_password_are_distinct`, `test_forgot_password_never_reveals_accounts` |
| 13 SQL injection | ✅ catalogue search | parameterised queries only; `test_search_handles_hostile_input` (quotes, `%`, `_`, backslash, emoji, SQL fragments) |
| 14 Uploads | ⬜ | |
| 15 Secrets | ⚠️ scanner + production config validation verified; log redaction untested | `scripts/check-secrets.py`, `test_settings.py` |
| 16 Error leakage | ✅ | `test_app_errors_and_unexpected_errors_are_formatted` (no internal detail in 500) |
| 17 Spam | ✅ contact + newsletter | honeypot, minimum fill time, rate limits: `test_contact_spam_is_silently_dropped`, `test_contact_is_rate_limited` |
| 18 Security headers | ⚠️ API headers verified; SPA CSP/HSTS pending deploy config | `test_security_headers_present` |
| 19 CORS | ⬜ | |
| 20 Guest order access | ✅ | 256-bit HMAC-derived token, only its hash stored; header `X-Order-Access-Token`; email link uses a URL fragment (never sent to servers or logs); `test_guest_order_needs_its_access_token`, other customers get 404 |
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
