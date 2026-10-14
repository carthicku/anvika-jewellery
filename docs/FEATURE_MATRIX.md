# Feature Matrix

Status: ⬜ not started · 🟡 in progress · ⚠️ partial / unverified · ✅ implemented **and verified by
the test listed**. Update this file whenever a feature changes state.

| Area | Feature | Route / API | Phase | Status | Evidence |
|------|---------|-------------|:-:|:-:|----------|
| Foundation | Backend app factory, config, error format, health check | `/api/v1/health` | 1 | ✅ | `tests/api/test_foundation.py`, `tests/unit/test_settings.py` |
| Foundation | Frontend shell, routing, layout | all | 1 | ✅ | `src/router.test.tsx`, `src/api/client.test.ts`, `e2e/smoke.spec.ts` |
| Foundation | Local DB, migrations, seed | CLI | 1/3 | ⚠️ | DB + migrations verified (fixtures + `alembic check`); seed arrives in Phase 3 |
| Storefront | Home page | `/` | 2/3 | ⬜ | |
| Storefront | Collections & categories | `/collections`, `/collections/:slug` | 2/3 | ⬜ | |
| Storefront | Filters, sorting, pagination (URL state) | `/products` | 3 | ⬜ | |
| Storefront | Search + suggestions | `/search`, `/search/suggest` | 3 | ⬜ | |
| Storefront | Product details, gallery, variants, breakdown | `/products/:slug` | 2/3/5 | ⬜ | |
| Storefront | PIN-code delivery check | `/shipping/pincode/{pin}` | 5 | ⬜ | |
| Storefront | Recently viewed | browser storage | 2 | ⬜ | |
| Storefront | Supporting & policy pages (editable) | `/about` … `/refund-policy` | 2/7 | ⬜ | |
| Storefront | Contact form, newsletter | `/contact`, `/newsletter/*` | 3 | ⬜ | |
| Storefront | 404 page | `*` | 1 | ✅ | `src/router.test.tsx`, `e2e/smoke.spec.ts` |
| Accounts | Register / login / logout | `/register`, `/login` | 4 | ⬜ | |
| Accounts | Email verification | `/verify-email` | 4 | ⬜ | |
| Accounts | Forgot / reset password | `/forgot-password`, `/reset-password` | 4 | ⬜ | |
| Accounts | Profile, addresses | `/account/profile`, `/account/addresses` | 4 | ⬜ | |
| Accounts | Security: change password, sessions | `/account/security` | 4 | ⬜ | |
| Accounts | Order history & detail with timeline | `/account/orders` | 6 | ⬜ | |
| Wishlist | Guest (browser) + signed-in + merge | `/wishlist`, `/account/wishlist` | 4 | ⬜ | |
| Cart | Server cart, guest cookie, merge on login | `/cart` | 5 | ⬜ | |
| Pricing | Engine (fixed, weight-based, making, wastage, stones, tax, rounding) | service | 5 | ⬜ | |
| Pricing | Automatic discounts + coupons | `/cart/coupon` | 5 | ⬜ | |
| Pricing | Price-change acceptance | `/cart/accept-prices` | 5 | ⬜ | |
| Checkout | Quote, address, shipping, terms, idempotent order creation | `/checkout` | 6 | ⬜ | |
| Payments | Razorpay order + verify + fetch | `/payments/verify` | 6 | ⬜ | |
| Payments | Webhooks (idempotent) | `/webhooks/razorpay` | 6 | ⬜ | |
| Payments | Retry, expiry, reconciliation, late capture | jobs | 6 | ⬜ | |
| Payments | Dev simulator (non-production) | `/payments/simulator/pay` | 6 | ⬜ | |
| Orders | Confirmation page (owner / guest token) | `/order-confirmation/:ref` | 6 | ⬜ | |
| Orders | Cancellation | `/orders/{ref}/cancel` | 6 | ⬜ | |
| Orders | Returns / exchanges | `/orders/{ref}/returns` | 7 | ⬜ | |
| Email | Outbox + templates + file sink + SMTP | jobs | 6 | ⬜ | |
| Admin | Auth, RBAC, audit logs | `/admin/*` | 7 | ⬜ | |
| Admin | Dashboard | `/admin` | 7 | ⬜ | |
| Admin | Products, variants, images | `/admin/products` | 7 | ⬜ | |
| Admin | Categories, collections | `/admin/categories`, `/admin/collections` | 7 | ⬜ | |
| Admin | Inventory & movements | `/admin/inventory` | 7 | ⬜ | |
| Admin | Orders, shipments, refunds | `/admin/orders` | 7 | ⬜ | |
| Admin | Customers | `/admin/customers` | 7 | ⬜ | |
| Admin | Discounts, coupons | `/admin/discounts`, `/admin/coupons` | 7 | ⬜ | |
| Admin | Gold rates (preview, confirm, history) | `/admin/gold-rates` | 7 | ⬜ | |
| Admin | Shipping methods & zones | `/admin/shipping` | 7 | ⬜ | |
| Admin | Content pages, reviews moderation | `/admin/content`, `/admin/reviews` | 7 | ⬜ | |
| Admin | Returns | `/admin/returns` | 7 | ⬜ | |
| Admin | Settings (store, tax, announcement) | `/admin/settings` | 7 | ⬜ | |
| Admin | Optional TOTP MFA | `/account/security` | 7 | ⬜ | |
| SEO | Metadata, canonical, OG, JSON-LD, sitemap, robots | — | 8 | ⬜ | |
| Quality | Playwright journeys J1–J12 | `frontend/e2e` | 8 | ⬜ | |
