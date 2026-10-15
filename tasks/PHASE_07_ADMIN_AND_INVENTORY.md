# Phase 7 — Administration

Goal: the owner can run the store without editing code.

## Tasks
- [x] Admin layout (lazy chunk), nav filtered by permissions (cosmetic), admin route guard
- [x] Audit log service used by every admin mutation
- [x] Dashboard: orders today, paid revenue (only `paid`), pending, payment-review, low stock, recent
      orders, best sellers (paid orders only), stale-rate warning, date filter
- [x] Products: list/search/filter, create/edit (details, pricing model, making, wastage, purity, SEO,
      flags, status), variants, stock initialisation, image upload (Pillow → WebP sizes) / reorder /
      alt text / delete, live price preview, preview link
- [x] Categories, collections (with product assignment)
- [x] Inventory: levels, adjust (reason required), movement history, low-stock threshold
- [x] Orders: list/filter/search, detail (items, breakdown, payments, events, audit), status transitions,
      shipments, cancellation, refunds (`orders:refund`), notes
- [x] Customers: list/search, detail
- [x] Discounts, coupons CRUD
- [x] Gold rates: current, history, preview of affected prices, large-change confirmation
- [x] Shipping methods & zones
- [x] Content pages editor (markdown, preview)
- [ ] Reviews: verified-purchase submission + moderation
- [ ] Returns workflow (customer request + admin decisions + restock) incl. `return_requests` table
- [x] Order status / shipment / refund emails (triggered by admin actions)
- [x] Execute requested refunds with Razorpay (`payments.refund`), refund webhooks end to end
- [x] Dashboard list of `payment_review` orders and stale gold-rate warning
- [x] Settings (store info placeholders, announcement, tax rates, thresholds)
- [x] Audit logs viewer; staff user management (admin only)
- [ ] Optional TOTP MFA for staff/admin
- [x] Tests: admin permission matrix for every route; product/inventory/gold-rate/coupon/order admin
      flows; e2e J8/J9 (+ admin component tests still to add)

## Acceptance
J8, J9, J10 pass; every admin mutation is audited.

Progress notes (2026-10-15):
- Backend admin API complete for operations, catalogue and store settings (48 tests in
  `test_admin_ops.py`, `test_admin_catalogue.py`, `test_admin_store.py`); every `/admin` route
  declares a permission (guard test).
- Admin UI built and verified end to end (`e2e/admin.spec.ts`, axe clean on desktop and phone).
- Defects found while testing and fixed: product attributes replaced in the wrong order (unique
  clash); reloaded product kept a stale photo list; product form lost its category when opened
  directly; dashboard showed gross revenue only (now net of refunds); wide tables pushed the page
  sideways and were not keyboard-scrollable.
- Remaining: returns workflow, reviews, optional TOTP MFA, admin component tests.
