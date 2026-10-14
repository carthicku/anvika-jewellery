# Feature Matrix

Status: ⬜ not started · 🟡 in progress · ⚠️ partial / unverified · ✅ implemented **and verified by
the test listed**. Update this file whenever a feature changes state.

| Area | Feature | Route / API | Phase | Status | Evidence |
|------|---------|-------------|:-:|:-:|----------|
| Foundation | Backend app factory, config, error format, health check | `/api/v1/health` | 1 | ✅ | `tests/api/test_foundation.py`, `tests/unit/test_settings.py` |
| Foundation | Frontend shell, routing, layout | all | 1 | ✅ | `src/router.test.tsx`, `src/api/client.test.ts`, `e2e/smoke.spec.ts` |
| Foundation | Local DB, migrations, seed | CLI | 1/3 | ✅ | `alembic check`; seed idempotency verified (2 runs → same counts); `test_database_safety.py` |
| Storefront | Home page | `/` | 2/3 | ✅ | `src/router.test.tsx`, `e2e/smoke.spec.ts`, axe scan |
| Storefront | Collections & categories | `/collections`, `/collections/:slug` | 2/3 | ✅ | `test_catalogue.py` (listings), `e2e/browse.spec.ts` |
| Storefront | Filters, sorting, pagination (URL state) | `/products` | 3 | ✅ | `test_catalogue.py` filters/sort/pagination; `storefront.test.tsx` listing filters |
| Storefront | Search + suggestions | `/search`, `/search/suggest` | 3 | ✅ | `test_search_handles_hostile_input`, `e2e/browse.spec.ts` search test |
| Storefront | Product details, gallery, variants, breakdown | `/products/:slug` | 2/3/5 | ✅ | `test_product_detail_with_variant_breakdowns`, `storefront.test.tsx` product page (add-to-cart arrives in Phase 5) |
| Storefront | PIN-code delivery check | `/shipping/pincode/{pin}` | 3 | ✅ | `test_content.py` PIN tests, `storefront.test.tsx`, `e2e/browse.spec.ts` |
| Storefront | Recently viewed | browser storage | 2 | ⚠️ | Implemented (`ProductPage` + `/products?slug=`); no dedicated test yet |
| Storefront | Supporting & policy pages (editable) | `/about` … `/refund-policy` | 2/7 | ⚠️ | Pages render from DB (`e2e/smoke.spec.ts` all routes); admin editing is Phase 7 |
| Storefront | Contact form, newsletter | `/contact`, `/newsletter/*` | 3 | ✅ | `test_content.py` (validation, honeypot, rate limit, idempotency), `storefront.test.tsx` contact form |
| Storefront | 404 page | `*` | 1 | ✅ | `src/router.test.tsx`, `e2e/smoke.spec.ts` |
| Accounts | Register / login / logout | `/register`, `/login` | 4 | ⬜ | |
| Accounts | Email verification | `/verify-email` | 4 | ⬜ | |
| Accounts | Forgot / reset password | `/forgot-password`, `/reset-password` | 4 | ⬜ | |
| Accounts | Profile, addresses | `/account/profile`, `/account/addresses` | 4 | ⬜ | |
| Accounts | Security: change password, sessions | `/account/security` | 4 | ⬜ | |
| Accounts | Order history & detail with timeline | `/account/orders` | 6 | ⬜ | |
| Wishlist | Guest (browser) + signed-in + merge | `/wishlist`, `/account/wishlist` | 2/4 | ⚠️ | Guest wishlist ✅ (`storefront.test.tsx`, `e2e/browse.spec.ts`); signed-in + merge in Phase 4 |
| Cart | Server cart, guest cookie, merge on login | `/cart` | 5 | ⬜ | |
| Pricing | Engine (fixed, weight-based, making, wastage, stones, tax, rounding) | service | 3 | ✅ | `tests/unit/test_pricing.py` (37 tests incl. worked example) |
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
| SEO | Metadata, canonical, OG, JSON-LD, sitemap, robots | — | 2/8 | ⚠️ | Titles/descriptions/canonical/OG + JSON-LD (non-sample only) + sitemap (`test_sitemap_lists_public_pages`); robots.txt in Phase 8 |
| Quality | Playwright journeys J1–J12 | `frontend/e2e` | 8 | ⬜ | |
