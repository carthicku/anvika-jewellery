# Phase 5 — Cart and Pricing

Goal: reliable, backend-calculated cart totals with transparent price changes.

## Tasks
- [ ] Models + migration: carts, cart_items, coupons, coupon_redemptions
- [ ] Pricing engine: automatic discounts (best per line), coupons (percent with cap / flat, min order,
      validity window, limits), coupon allocation (largest remainder), per-component tax, rounding to rupee
- [ ] Pricing context loader (rates, tax settings, discounts) + `gold_rate_stale` handling
- [ ] Cart service: guest cookie token (hashed), add/update/remove with stock + quantity limits,
      merge on login, price-change detection (increase blocks, decrease auto-applies), accept-prices
- [ ] Cart API + coupon endpoints
- [ ] Shipping quote (methods, free-above, zones, estimated delivery)
- [ ] Frontend: cart page (lines, stepper, remove, coupon, summary, notices), header cart count, add to
      cart / buy now on PDP, PIN-code checker
- [ ] Tests: pricing unit tests (full TEST_PLAN list), cart API, coupon errors, price-change scenarios

## Acceptance
J1 passes; J7 (cart part) passes; no price arithmetic in the frontend.
