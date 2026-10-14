# Phase 7 — Administration

Goal: the owner can run the store without editing code.

## Tasks
- [ ] Admin layout (lazy chunk), nav filtered by permissions (cosmetic), admin route guard
- [ ] Audit log service used by every admin mutation
- [ ] Dashboard: orders today, paid revenue (only `paid`), pending, payment-review, low stock, recent
      orders, best sellers (paid orders only), stale-rate warning, date filter
- [ ] Products: list/search/filter, create/edit (details, pricing model, making, wastage, purity, SEO,
      flags, status), variants, stock initialisation, image upload (Pillow → WebP sizes) / reorder /
      alt text / delete, live price preview, preview link
- [ ] Categories, collections (with product assignment)
- [ ] Inventory: levels, adjust (reason required), movement history, low-stock threshold
- [ ] Orders: list/filter/search, detail (items, breakdown, payments, events, audit), status transitions,
      shipments, cancellation, refunds (`orders:refund`), notes
- [ ] Customers: list/search, detail
- [ ] Discounts, coupons CRUD
- [ ] Gold rates: current, history, preview of affected prices, large-change confirmation
- [ ] Shipping methods & zones
- [ ] Content pages editor (markdown, preview), reviews moderation (+ customer review submission)
- [ ] Returns workflow (customer request + admin decisions + restock)
- [ ] Settings (store info placeholders, announcement, tax rates, thresholds)
- [ ] Audit logs viewer; staff user management (admin only)
- [ ] Optional TOTP MFA for staff/admin
- [ ] Tests: admin permission matrix for every route; product/inventory/gold-rate/coupon/order admin
      flows; e2e J8/J9

## Acceptance
J8, J9, J10 pass; every admin mutation is audited.
