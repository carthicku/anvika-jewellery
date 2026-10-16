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
* Refunds are executed from Admin → Orders through the payment gateway; only the simulator and a
  mocked Razorpay API have been exercised so far.
* S3-compatible photo storage is unit-tested with botocore's Stubber, not against a real bucket.
* **Vercel deployment is configured but has never been deployed** (`vercel.json`, ADR-0011). Vercel
  Services is a beta feature; photo uploads are capped at 4.5 MB by Vercel; per-minute cron (order
  expiry, payment reconciliation, queued emails) needs the Pro plan; cron wiring under Services,
  the Supabase pooler settings and S3 uploads are unverified until a first Preview deployment
  (DEPLOYMENT.md §7).
* **Docker not verified**: `backend/Dockerfile` and `deploy/docker-compose.prod.yml` have never been
  built or run (Docker is not installed on the development machine). The Caddyfile was validated
  and exercised locally with the official Caddy binary. Build and start the stack on staging first.
* **Mobile loading speed**: Lighthouse mobile performance 79–83, LCP ≈ 3.5–3.8 s under simulated
  slow 4G (desktop 94–99). A client-rendered SPA must run its JavaScript before requesting images;
  pre-rendering public pages is the planned improvement. Measured locally only (PERFORMANCE_REVIEW).
* API timings with 1,000 products were measured in-process against local PostgreSQL, not on
  Supabase's production tier or over the internet.
* **Home necklace hero (ADR-0010)**: the 3D chunk (three.js + React Three Fiber + GSAP) is
  ≈286 kB gzip. React Three Fiber v9 imports all of three.js, so it can't be tree-shaken. It loads
  only after the page has finished loading and is idle, so the headline is unaffected, but on
  throttled phones running it adds main-thread work (see PERFORMANCE_REVIEW). Browsers without
  WebGL get the dark hero with its text and no animation. The necklace is an illustration, not a
  product.
* No manual (human) keyboard and screen-reader pass has been recorded yet; automated keyboard and
  axe checks pass.
* Staff accounts are created by promoting a registered account; there is no invitation email.
* The payment simulator remembers simulated payments in memory only; after an API restart the
  reconciliation job cannot see them (development only — no money involved).
* Guests keep their order access token in `sessionStorage` for the current tab; reopening the
  order later needs the link from the confirmation email.
* Admin TOTP MFA is **not built** (deferred). Mitigations: strong unique passwords, rate-limited
  sign-in, short sessions, sessions revoked on role change, every admin action audited. Recommended
  before giving more people staff access.
* Returns: return shipping (courier pickup, labels) is arranged by staff outside the system; the
  suggested refund excludes delivery charges (staff can change the amount). Only signed-in
  customers can write reviews; guests' orders can be returned but not reviewed.
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
