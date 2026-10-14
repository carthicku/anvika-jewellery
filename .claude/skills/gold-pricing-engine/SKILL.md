---
name: gold-pricing-engine
description: Use whenever code or data touches jewellery prices — gold rates, purity, weights, making charges, wastage, stones, discounts, coupons, GST/tax, rounding, price breakdowns, price-change acceptance, or order price snapshots. Reviews calculations for Decimal correctness, configurability, auditability and backend authority.
---

# Gold pricing engine

The specification is `docs/architecture/PRICING_ENGINE.md`. **The code must match it exactly. If they
disagree, stop and resolve which one is wrong.** Code: `backend/app/services/pricing.py` (pure
functions) and `pricing_context.py` (DB loading). Tests: `backend/tests/unit/test_pricing.py`.

## Invariants
1. `decimal.Decimal` everywhere. Construct from strings/ints, never from floats
   (`Decimal("7000.00")`, not `Decimal(7000.0)`). Round with `money()` (2 dp, ROUND_HALF_UP).
   The grand total is rounded to the rupee and the difference is shown as `rounding_adjustment`.
2. The backend is the only calculator. The frontend renders `breakdown` rows. Browser
   `expected_total` is only a consent check.
3. No hard-coded market rates, tax rates, making charges or wastage. Rates come from `gold_rates`
   (latest effective), tax from `store_settings['tax']`, making/wastage per product.
4. Each order stores the components (`order_items` line columns) **and** the inputs
   (`price_inputs`: rate id, rate, purity, weights, making config, tax rates, discount) plus
   `orders.pricing_context`. Never recompute historical orders from current data.
5. Missing inputs make the item **unpurchasable**. They never default to zero (e.g. no rate for the
   purity).
6. Discounts: at most one automatic discount per line (best for the customer), one coupon per order.
   Coupon allocation uses largest remainder so the parts sum exactly.
7. Price increases block checkout until accepted. Decreases auto-apply with a notice. Order prices are
   frozen for the payment window.

## Required tests when changing pricing
- [ ] Worked example from PRICING_ENGINE.md §4 still equals ₹32,301.00 (rounding +0.20)
- [ ] Each making type (per_gram, percent, flat, none), wastage on/off, stones/other charges, fixed model
- [ ] Each discount kind; best-discount selection; coupon cap, minimum order and validity
- [ ] Allocation sums exactly; tax per component; rounding half-up at .50 and down at .49
- [ ] Missing rate → not purchasable
- [ ] Gold-rate change → cart flags the increase; order creation with a stale expected_total → `PRICE_CHANGED`
- [ ] Order snapshot unchanged after later rate/product edits

## Tax caution
GST defaults (3%/3%/3%/0%) are placeholders pending professional advice (ASSUMPTIONS P3). Do not
change tax logic based on assumptions. Make it configurable and document it.
