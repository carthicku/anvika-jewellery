# Phase 5 — Cart and Pricing  ✅ complete (2026-10-14)

Goal: reliable, backend-calculated cart totals with transparent price changes.

## Tasks
- [x] Models + migration: carts, cart_items, coupons, coupon_redemptions
- [x] Pricing engine: automatic discounts (best per line), coupons (percent with cap / flat, min order,
      validity window, limits), coupon allocation (largest remainder), per-component tax, rounding to rupee
- [x] Pricing context loader (rates, tax settings, discounts)
- [ ] `gold_rate_stale` handling (dashboard warning + optional checkout block) → moved to Phase 6/7
- [x] Cart service: guest cookie token (hashed), add/update/remove with stock + quantity limits,
      merge on login, price-change detection (increase blocks, decrease auto-applies), accept-prices
- [x] Cart API + coupon endpoints
- [x] Shipping quote (methods, free-above, zones, estimated delivery)
- [x] Frontend: cart page (lines, stepper, remove, coupon, summary, notices), header cart count, add to
      cart / buy now on PDP, PIN-code checker
- [x] Tests: pricing unit tests (full TEST_PLAN list), cart API, coupon errors, price-change scenarios

## Acceptance
J1 passes; J7 (cart part) passes; no price arithmetic in the frontend.

Notes:
- The pricing engine (discounts, coupons, GST, rounding) and the PIN-code check were already built in
  Phase 3; this phase connected them to carts.
- "Proceed to checkout" is shown but disabled with an explanation until checkout ships in Phase 6;
  "Buy now" adds to the cart and opens it.
- J7 (gold-rate change → cart) is covered by API tests; an end-to-end version needs the admin
  gold-rate screen (Phase 7).
- Defects found and fixed: cart overflowed sideways on phones; line totals included the coupon share
  (looked like a pricing error) — now price each × quantity.
