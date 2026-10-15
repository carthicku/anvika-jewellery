# Known Limitations

Honest list of what the system does not do (yet), what is unverified, and what depends on the
owner. Keep it current. Each item states its impact and the plan.

## Requires the owner / external parties
| Item | Impact | Plan |
|------|--------|------|
| Brand name, logo, contact details, GSTIN are placeholders | Cannot launch | Owner provides; configure in Admin → Settings |
| GST rates are placeholder defaults | Possible tax errors | CA review before launch |
| Policy pages are drafts | Legal risk | Owner + lawyer approval |
| Razorpay test keys not yet provided | The real sandbox has not been exercised; only the simulator and mocked Razorpay API | Owner creates test keys (PAYMENT_PROVIDER_SETUP.md) |
| Supabase project not yet created | Production DB untested; local PostgreSQL 17 used | Owner creates the project (DEPLOYMENT.md) |
| No SMTP provider chosen | Emails only go to the dev sink | Owner chooses a provider (EMAIL_SETUP.md) |
| No courier integration | Tracking entered manually | Optional future integration (SHIPPING_SETUP.md) |
| Product photography | Sample illustrations only | Owner uploads real photos |

## Product scope
* No cash on delivery, gift cards, loyalty points, multi-currency, or multiple languages.
* No live gold-rate feed (manual entry by design until a provider is vetted).
* PIN-code check validates format and configured zones only (no city/state lookup).
* Client-side rendered SPA: social-media link previews (Open Graph) for product pages need
  pre-rendering or an edge function to be fully reliable.

## Technical
* Razorpay has been exercised only against a mocked API in automated tests; a run with real
  test-mode keys is pending (no keys provided). No real money has moved.
* Refunds are recorded (`requested`) but executed with Razorpay only once the admin refund screen
  exists (Phase 7). Status/shipment/refund emails also arrive with Phase 7.
* The payment simulator remembers simulated payments in memory only; after an API restart the
  reconciliation job cannot see them (development only — no money involved).
* Guests keep their order access token in `sessionStorage` for the current tab; reopening the
  order later needs the link from the confirmation email.
* Admin TOTP MFA: planned for Phase 7, not yet implemented.
* Registration reveals whether an email already has an account (`EMAIL_IN_USE`) — a usability
  trade-off mitigated by rate limiting. Passwords are not checked against breached-password lists.
* End-to-end tests run against a backend with `RATE_LIMIT_ENABLED=false` (limits are covered by API
  tests).
* Background jobs run in-process. For multiple app instances they are safe (SKIP LOCKED) but
  duplicated; a dedicated scheduler could replace them later.
* Rate limiting is per IP/email in PostgreSQL. There is no WAF or bot management.
* No error-tracking service (e.g. Sentry) integrated.
* Docker Compose files cannot be verified on the development machine (Docker is not installed).

## Unverified
Everything in FEATURE_MATRIX not marked ✅.
