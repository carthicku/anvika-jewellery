# Assumptions and Decisions

This file records every assumption made while building the store, and every decision that the
business owner may want to revisit. Significant technical decisions also have an Architecture
Decision Record (ADR) in [`architecture/ADR/`](architecture/ADR/).

Status legend: **Assumed** (we chose a default, owner should confirm) · **Decided** (technical
decision, documented in an ADR) · **Owner action** (cannot proceed to launch without the owner).

---

## 1. Business facts

| # | Topic | Assumption / placeholder | Status |
|---|-------|--------------------------|--------|
| B1 | Brand name | Working name **"Anvika"** taken from the project folder name. It is configured in one place (`STORE_NAME` backend setting and `VITE_STORE_NAME` frontend variable) and can be changed without code edits. | Assumed |
| B2 | Logo | A text wordmark is used until a real logo is supplied. | Owner action |
| B3 | Business address, GSTIN, phone, support email | Not known. Shown as clearly marked placeholders (e.g. `[Business address — to be configured]`) editable in **Admin → Settings**. | Owner action |
| B4 | Certifications / hallmarking | The store does **not** claim BIS hallmarking, HUID, or certificates for any product unless an administrator enters that information for that product. Sample products show no hallmark claims. | Decided |
| B5 | Customer reviews, testimonials, awards, sales figures | None are invented. Reviews only appear after real customers submit them and an admin approves them. | Decided |
| B6 | Policies (shipping, returns, refunds, privacy, terms) | Draft templates are provided and **marked as drafts requiring owner and legal review**. They are editable in **Admin → Content**. | Owner action |
| B7 | Product photography | Sample products use original, clearly-labelled illustration placeholders (no third-party photos). Real photographs are uploaded through the admin. | Decided |
| B8 | Sample catalogue | Seed data is fictional and flagged `is_sample` where shown. It must be removed or replaced before launch. | Decided |

## 2. Pricing and tax

| # | Topic | Assumption | Status |
|---|-------|------------|--------|
| P1 | Gold rates | Entered manually by an admin (per purity, per gram, INR) with an effective timestamp and source note. **No live gold-rate API** is integrated; one can be added later after its terms and reliability are verified. | Decided |
| P2 | Seed gold rates | Seed rates are **illustrative development values only**, labelled as such, and are not market data. | Decided |
| P3 | GST rates | Defaults: 3% on metal value, 3% on making charges, 3% on stones/other materials, 0% on shipping. These are **placeholder defaults** that are configurable in Admin → Settings and must be confirmed by a qualified Indian tax professional before launch. | Owner action |
| P4 | Tax display | Catalogue prices are displayed **inclusive of tax** ("Incl. of all taxes") with an itemised breakdown that shows the tax separately. | Assumed |
| P5 | Rounding | Every component is calculated with `Decimal` and rounded to paise (2 dp, ROUND_HALF_UP). The order grand total is rounded to the nearest whole rupee, and the difference is shown as a "Rounding adjustment" line. | Decided |
| P6 | Wastage | Only applied when explicitly configured on a product (percentage of metal value). Default is no wastage. | Decided |
| P7 | Discounts | At most **one automatic discount per line** (the best one for the customer) plus **at most one coupon per order**. Coupons are allocated across lines proportionally to pre-tax value so tax is calculated on the discounted value. | Assumed |
| P8 | Price validity | Prices are recalculated by the backend on every cart read and at checkout. If the price differs from what the customer last saw, checkout is blocked until the customer explicitly accepts the new price. Once an order is created its prices are locked for the payment window (default 30 minutes). | Decided |
| P9 | Large gold-rate changes | A rate change of more than 5% (configurable) from the current rate requires an explicit confirmation flag from the admin. | Decided |

## 3. Commerce operations

| # | Topic | Assumption | Status |
|---|-------|------------|--------|
| C1 | Market | India only. Shipping addresses must be Indian (6-digit PIN code, Indian state/UT). | Decided |
| C2 | Currency | INR only. Currency is still stored explicitly on every monetary record. | Decided |
| C3 | Shipping | Admin-configured shipping methods (flat fee, optional free-shipping threshold, delivery-day range) and optional serviceable PIN-code prefixes. No courier API is integrated yet; tracking numbers and URLs are entered by an admin. | Decided |
| C4 | PIN-code validation | Format validation (6 digits, first digit 1–9) plus admin-configured serviceability. No PIN → city/state lookup is performed because no verified dataset or API has been chosen. | Decided |
| C5 | Payment window | A pending order reserves stock for 30 minutes (configurable). After that it expires and stock is released. | Assumed |
| C6 | Cancellations | Customers can cancel an order themselves while it is `pending_payment` or `confirmed` (paid but not yet being processed). After that they can only request cancellation. Paid cancellations create a refund record; an admin triggers the actual Razorpay refund. | Assumed |
| C7 | Returns / exchanges | Eligibility is configured per product (`return_eligible`, `exchange_eligible`, window in days). Customers submit a request; an admin approves or rejects it. | Assumed |
| C8 | Cash on delivery | Not offered. Only Razorpay online payment is supported initially. | Assumed |
| C9 | Order reference | Format `ANV-YYMMDD-XXXXXX` (random, non-sequential). The prefix is configurable. | Decided |
| C10 | Guest checkout | Supported. Guests view their order through a private access link (secret token), not by reference alone. | Decided |
| C11 | Guest wishlist | Stored in the browser (product slugs only — not sensitive) and merged into the account at sign-in. | Decided |

## 4. Technical decisions (see ADRs)

| # | Decision | ADR |
|---|----------|-----|
| T1 | Modular monolith: React SPA + FastAPI + PostgreSQL | [ADR-0001](architecture/ADR/0001-modular-monolith.md) |
| T2 | **Supabase is used as managed PostgreSQL only** (plus optionally its S3-compatible Storage for images). Authentication is implemented in FastAPI, not Supabase Auth, because the spec requires the backend to own authentication and authorization. | [ADR-0002](architecture/ADR/0002-supabase-as-managed-postgres.md) |
| T3 | Cookie-based auth: short-lived JWT access cookie + rotating opaque refresh cookie backed by a `user_sessions` table; double-submit CSRF token | [ADR-0003](architecture/ADR/0003-cookie-auth-and-csrf.md) |
| T4 | Synchronous SQLAlchemy 2.x with psycopg 3 (simpler for beginners; FastAPI runs sync endpoints in a thread pool) | [ADR-0004](architecture/ADR/0004-sync-sqlalchemy.md) |
| T5 | Razorpay is called through its REST API with `httpx` rather than the Python SDK (fewer dependencies, easy to mock) | [ADR-0005](architecture/ADR/0005-razorpay-rest-integration.md) |
| T6 | A **payment simulator** exists for local development and automated tests only. It cannot be enabled when `APP_ENV=production` (startup fails), and orders paid through it are permanently marked `provider=simulator`. | [ADR-0005](architecture/ADR/0005-razorpay-rest-integration.md) |
| T7 | Local development database: PostgreSQL 17 via the `embedded-postgres` npm package (Docker is not installed on the development machine). A `docker-compose.yml` is also provided for machines that have Docker. | [ADR-0006](architecture/ADR/0006-local-embedded-postgres.md) |
| T8 | Inventory uses a row-locked `inventory_levels` table (`on_hand`, `reserved`) with database CHECK constraints plus a movement ledger | [ADR-0007](architecture/ADR/0007-inventory-locking.md) |
| T9 | Transactional emails go through an `email_outbox` table (idempotent) and a pluggable sender: `file` sink in development, SMTP in production | [ADR-0008](architecture/ADR/0008-email-outbox.md) |
| T10 | Python 3.13 (3.12 on this machine is broken; 3.11+ remains supported by the code) | — |
| T11 | TypeScript pinned to 5.9.x (openapi-typescript 7 requires TS 5; typescript-eslint supports < 6.1); ESLint 10 with the maintained `eslint-plugin-jsx-a11y-x` fork | [ADR-0009](architecture/ADR/0009-frontend-stack.md) |
| T19 | Local dev ports: web 5180, API 8010 (5173 and 8000 are occupied by other projects on the dev machine) | — |
| T12 | Tailwind CSS v4 with design tokens declared via `@theme`; accessible primitives from Radix (`radix-ui`) styled in shadcn/ui fashion instead of running the shadcn generator | [ADR-0009](architecture/ADR/0009-frontend-stack.md) |
| T13 | Frontend talks to the API on the **same origin** (`/api/v1`). Vite proxies in development; in production a reverse proxy/rewrite (or an `api.` subdomain on the same registrable domain) is used so `SameSite=Lax` cookies work | [ADR-0003](architecture/ADR/0003-cookie-auth-and-csrf.md) |
| T14 | API contract: backend exports `openapi.json`; frontend generates TypeScript types with `openapi-typescript` | [ADR-0009](architecture/ADR/0009-frontend-stack.md) |
| T15 | Rate limiting is stored in PostgreSQL (`rate_limit_buckets`) so limits hold across multiple workers and restarts | [SECURITY_MODEL](architecture/SECURITY_MODEL.md) |
| T16 | Roles: `customer`, `staff`, `admin`. Permissions are a fixed role→permission map in code (`app/core/permissions.py`) rather than editable DB rows, to avoid privilege-escalation via data | [AUTHENTICATION](architecture/AUTHENTICATION.md) |
| T17 | Multi-factor authentication for admins (TOTP) is planned for Phase 7 as optional; not required for launch of the MVP but recommended | [SECURITY_MODEL](architecture/SECURITY_MODEL.md) |
| T18 | SEO: the site is a client-rendered SPA. React 19 native `<title>/<meta>` hoisting is used for metadata; the backend generates `sitemap.xml`. Pre-rendering/SSR is a documented future improvement | [PERFORMANCE_REVIEW](quality/PERFORMANCE_REVIEW.md) |

## 5. Open questions for the owner

1. Confirm the brand name, logo, contact details, GSTIN and registered address.
2. Confirm GST treatment with a chartered accountant (see P3).
3. Provide Razorpay **test** keys (key id, key secret, webhook secret) to test the real sandbox.
4. Create a Supabase project (region: Mumbai `ap-south-1` recommended) and share the connection string through a local `.env` file — never in chat or Git.
5. Choose an SMTP provider (e.g. Amazon SES, Postmark, Zoho ZeptoMail, Brevo) and verify the sending domain.
6. Choose a shipping partner (e.g. Shiprocket, Delhivery, BlueDart) if courier API integration is wanted.
7. Approve or rewrite every policy page.
