# Product Requirements

## 1. Vision
An online store for a gold jewellery retailer in India that feels as refined and trustworthy as a
good jewellery showroom. Prices are transparent and explained line by line. Checkout is quick on a
phone. The owner can run the catalogue, gold rates, stock and orders without touching code.

## 2. Users
| Persona | Needs |
|---------|-------|
| **Shopper (guest)** | Browse beautiful, fast pages; understand purity, weight and price breakdown; buy without being forced to register; trust the payment. |
| **Customer (signed in)** | Saved addresses, order history and tracking, wishlist, easy returns. |
| **Store staff** | Add products, upload photos, manage stock, process orders, add tracking. |
| **Owner / admin** | Everything staff can do, plus gold rates, taxes, coupons, settings, refunds, user roles, audit logs. |

## 3. Scope
### In scope (v1)
* Storefront: home, collections and categories, search, product details, wishlist, cart, checkout,
  order confirmation, supporting content and policy pages, 404.
* Accounts: register, login, logout, email verification (configurable), password reset, profile,
  addresses, orders, wishlist, security (password, sessions).
* Pricing engine: fixed and weight-based products, making charges (per gram / % / flat), optional
  wastage, stones/other charges, automatic discounts, coupons, configurable GST, rounding, price
  change acceptance, auditable snapshots.
* Inventory: variant-level stock, reservations, movement ledger, low-stock alerts.
* Payments: Razorpay (test mode first) with signature verification, webhooks, retries,
  reconciliation, refunds.
* Admin dashboard and all admin pages listed in the master brief (section 7).
* Transactional emails through an outbox (dev sink locally).
* SEO basics (metadata, canonical URLs, structured data from verified fields, sitemap, robots).
* Accessibility target WCAG 2.2 AA.

### Out of scope (v1, may come later)
Multiple languages (the architecture keeps copy in one place to ease i18n later), multiple
currencies, cash on delivery, courier API integration (manual tracking entry only), live gold-rate
feed, customer-uploaded review photos, gift cards, loyalty points, server-side rendering, native
mobile apps.

## 4. Functional requirements
Detailed per-route requirements are in the master brief (sections 5–7) and are tracked
feature-by-feature in [FEATURE_MATRIX.md](FEATURE_MATRIX.md). Testable acceptance criteria are in
[ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md).

## 5. Non-functional requirements
| Area | Requirement |
|------|-------------|
| Security | See [SECURITY_MODEL.md](architecture/SECURITY_MODEL.md). Backend-only business rules, no secrets in the frontend. |
| Correctness | Money in `Decimal`/`NUMERIC`; DB constraints for critical invariants; idempotent payment processing. |
| Performance | Product listing API p95 < 300 ms with 1,000 products on the production DB tier; initial JS for the storefront < 200 KB gzip (admin code split out). Measured, not assumed — see PERFORMANCE_REVIEW. |
| Accessibility | WCAG 2.2 AA target; keyboard-only checkout possible; visible focus; reduced motion respected. |
| Responsiveness | 320 px to 1920 px; touch targets ≥ 44 × 44 px. |
| Maintainability | Typed end to end; linting and formatting enforced; documented conventions; tests for business rules. |
| Observability | Structured logs with request ids; payment events stored; audit log for admin actions. |
| Privacy | Minimal personal data; no sensitive data in logs; private pages not indexed. |

## 6. Success metrics (to be measured after launch)
Checkout conversion rate, payment success rate, average time to checkout on mobile, number of
payment-review orders (should be ~0), support contacts about pricing (should fall as breakdowns
are clear).
