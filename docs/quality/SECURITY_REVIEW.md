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
| 1 Server-side pricing | ⬜ Not yet verified | |
| 2 Payment verification | ⬜ | |
| 3 Webhook HMAC + idempotency | ⬜ | |
| 4 Overselling protection | ⬜ | |
| 5 Duplicate orders | ⬜ | |
| 6 Brute-force protection | ⬜ | |
| 7 XSS / CSP | ⚠️ partial | Markdown rendered without raw HTML (react-markdown default); JSON-LD escapes `<`; CSP pending deploy config |
| 8 CSRF | ✅ middleware verified | `test_foundation.py` CSRF tests (missing/mismatched/foreign origin/webhook exemption) |
| 9 Refresh rotation | ⬜ | |
| 10 IDOR | ⬜ | |
| 11 Admin RBAC | ⬜ | |
| 12 Enumeration | ⬜ | |
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
