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
| Storefront | Supporting & policy pages (editable) | `/about` … `/refund-policy` | 2/7 | ✅ | Pages render from DB (`e2e/smoke.spec.ts`); edited in Admin → Content (`test_staff_edit_content_pages`) |
| Storefront | Contact form, newsletter | `/contact`, `/newsletter/*` | 3 | ✅ | `test_content.py` (validation, honeypot, rate limit, idempotency), `storefront.test.tsx` contact form |
| Storefront | 404 page | `*` | 1 | ✅ | `src/router.test.tsx`, `e2e/smoke.spec.ts` |
| Accounts | Register / login / logout | `/register`, `/login` | 4 | ✅ | `test_auth.py`, `account.test.tsx`, `e2e/account.spec.ts` |
| Accounts | Email verification | `/verify-email` | 4 | ✅ | `test_register_sends_verification_email_and_verifies` |
| Accounts | Forgot / reset password | `/forgot-password`, `/reset-password` | 4 | ✅ | `test_forgot_password_never_reveals_accounts`, `test_reset_password_flow`, expiry + single-use tests |
| Accounts | Profile, addresses | `/account/profile`, `/account/addresses` | 4 | ✅ | `test_account.py`, `account.test.tsx`, `e2e/account.spec.ts` |
| Accounts | Security: change password, sessions | `/account/security` | 4 | ✅ | `test_change_password_keeps_current_session_only`, `test_list_and_revoke_sessions`, `test_logout_all` |
| Accounts | Order history & detail with timeline | `/account/orders` | 6 | ✅ | `test_signed_in_order_uses_account_email_and_is_private`, `e2e/checkout.spec.ts` (signed-in journey) |
| Wishlist | Guest (browser) + signed-in + merge | `/wishlist`, `/account/wishlist` | 2/4 | ✅ | `test_wishlist_add_remove_and_merge`, `test_wishlists_are_private`, `account.test.tsx` (merge on sign-in, server save), `e2e/browse.spec.ts` |
| Cart | Server cart, guest cookie, merge on login | `/cart` | 5 | ✅ | `tests/api/test_cart.py` (17), `cart.test.tsx`, `e2e/cart.spec.ts` |
| Pricing | Engine (fixed, weight-based, making, wastage, stones, tax, rounding) | service | 3 | ✅ | `tests/unit/test_pricing.py` (37 tests incl. worked example) |
| Pricing | Automatic discounts + coupons | `/cart/coupon` | 5 | ✅ | `test_pricing.py`, `test_valid_coupon_applies_with_cap`, `test_invalid_coupons_explain_why`, `test_coupon_below_minimum_is_kept_but_not_applied`, `e2e/cart.spec.ts` |
| Pricing | Price-change acceptance | `/cart/accept-prices` | 5 | ✅ | `test_price_increase_blocks_checkout_until_accepted`, `test_price_decrease_is_good_news_and_does_not_block`, `cart.test.tsx` |
| Checkout | Quote, address, shipping, terms, idempotent order creation | `/checkout` | 6 | ✅ | `tests/api/test_checkout.py` (21), `checkout.test.tsx`, `e2e/checkout.spec.ts` |
| Payments | Razorpay order + verify + fetch | `/payments/verify` | 6 | ✅ (mocked Razorpay; real test keys pending) | `test_full_checkout_against_mocked_razorpay`, `test_forged_signature_is_rejected`, `test_amount_mismatch_never_marks_paid` |
| Payments | Webhooks (idempotent) | `/webhooks/razorpay` | 6 | ✅ | `test_webhook_capture_confirms_once_and_ignores_duplicates`, `test_webhook_with_bad_signature_is_rejected_and_not_stored` |
| Payments | Retry, expiry, reconciliation, late capture | jobs | 6 | ✅ | `test_failed_payment_can_be_retried`, `test_unpaid_order_expires_and_releases_stock_and_coupon`, `test_late_capture_*`, `test_provider_outage_never_expires_an_order_blindly` |
| Payments | Dev simulator (non-production) | `/payments/simulator/pay` | 6 | ✅ | `test_simulator_endpoint_is_unavailable_with_a_real_provider`, production settings test |
| Orders | Confirmation page (owner / guest token) | `/order-confirmation/:ref` | 6 | ✅ | `test_guest_order_needs_its_access_token`, `e2e/checkout.spec.ts` |
| Orders | Cancellation | `/orders/{ref}/cancel` | 6 | ✅ | `test_cancel_*`, `e2e/checkout.spec.ts` |
| Orders | Returns / exchanges | `/orders/{ref}/returns` | 7 | ⬜ | |
| Email | Outbox + templates + file sink + SMTP | jobs | 6 | ⚠️ outbox, templates and file/memory sinks verified; SMTP not tried against a real server | `test_verified_payment_confirms_order_and_sells_stock` (confirmation email), auth email tests |
| Admin | Auth, RBAC, audit logs | `/admin/*` | 4/7 | ✅ | `test_every_admin_route_declares_a_permission`, `test_staff_permissions_are_limited`, audit viewer, `e2e/admin.spec.ts` (customers blocked) |
| Admin | Dashboard | `/admin` | 7 | ✅ | `test_dashboard_counts_only_paid_money`, e2e |
| Admin | Products, variants, images | `/admin/products` | 7 | ✅ | `test_admin_catalogue.py` (19), e2e J8 |
| Admin | Categories, collections | `/admin/categories`, `/admin/collections` | 7 | ✅ | `test_categories_crud_with_safety`, `test_collections_hold_ordered_products` |
| Admin | Inventory & movements | `/admin/inventory` | 7 | ✅ | `test_stock_adjustments_are_ledgered_and_audited`, `test_stock_cannot_drop_below_reserved`, e2e J9 |
| Admin | Orders, shipments, refunds | `/admin/orders` | 7 | ✅ (refunds via simulator/mocked Razorpay) | `test_fulfil_a_paid_order_end_to_end`, `test_partial_refund_*`, review resolution tests, e2e cancel + refund |
| Admin | Customers | `/admin/customers` | 7 | ✅ | `test_customer_list_and_detail` |
| Admin | Discounts, coupons | `/admin/discounts`, `/admin/coupons` | 7 | ✅ | `test_automatic_discount_changes_prices`, `test_coupons_are_created_uppercase_and_track_usage` |
| Admin | Gold rates (preview, confirm, history) | `/admin/gold-rates` | 7 | ✅ | `test_gold_rate_preview_shows_every_affected_price`, `test_large_rate_change_needs_confirmation_and_is_audited` |
| Admin | Shipping methods & zones | `/admin/shipping` | 7 | ✅ | `test_shipping_zones_limit_delivery`, `test_at_least_one_delivery_method_stays_active` |
| Admin | Content pages, reviews moderation | `/admin/content`, `/admin/reviews` | 7 | ⚠️ content ✅, reviews pending | `test_staff_edit_content_pages` |
| Admin | Returns | `/admin/returns` | 7 | ⬜ | |
| Admin | Staff users (promote, role, deactivate) | `/admin/staff` | 7 | ✅ | `test_admin_promotes_and_deactivates_staff`, `test_the_last_admin_cannot_be_removed` |
| Admin | Settings (store, tax, announcement) | `/admin/settings` | 7 | ✅ | `test_tax_settings_change_prices_and_are_audited`, `test_store_details_are_validated`, `test_announcement_links_must_be_safe` |
| Admin | Optional TOTP MFA | `/account/security` | 7 | ⬜ | |
| SEO | Metadata, canonical, OG, JSON-LD, sitemap, robots | — | 2/8 | ⚠️ | Titles/descriptions/canonical/OG + JSON-LD (non-sample only) + sitemap (`test_sitemap_lists_public_pages`); robots.txt in Phase 8 |
| Quality | Playwright journeys J1–J12 | `frontend/e2e` | 8 | ⬜ | |
