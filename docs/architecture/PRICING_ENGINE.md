# Gold Pricing Engine

Code: `backend/app/services/pricing.py` (pure calculation functions) and
`backend/app/services/pricing_context.py` (loads rates, tax settings and discounts from the database).
Tests: `backend/tests/unit/test_pricing.py`.

> **The backend is the only place prices are calculated.** The frontend displays the breakdown it
> receives. Nothing the browser sends (prices, totals, discounts) is used as an input.

## 1. Inputs

| Input | Source |
|-------|--------|
| Pricing model (`fixed` / `weight_based`) | `products.pricing_model` |
| Purity (24K/22K/18K/14K) | `products.purity` |
| Net gold weight (g) | `product_variants.net_gold_weight_g` |
| Gold rate per gram for the purity | latest `gold_rates` row with `effective_from <= now()` |
| Making charge type & value | `products.making_charge_type` ∈ {per_gram, percent, flat, none}, `making_charge_value` |
| Wastage % (optional) | `products.wastage_percent` (only when explicitly set) |
| Stone value, other charges | `product_variants.stone_value`, `other_charges` |
| Fixed price (pre-tax) | `product_variants.fixed_price` (fixed model only) |
| Tax rates | `store_settings['tax']`: `metal_percent`, `making_percent`, `stones_percent`, `shipping_percent` |
| Automatic discount | best applicable active row in `discounts` |
| Coupon | `coupons` row referenced by the cart |

All arithmetic uses Python `decimal.Decimal`. Helper `money(x)` = `x.quantize(Decimal("0.01"), ROUND_HALF_UP)`.

## 2. Unit price (one piece of one variant)

### Weight-based
```
metal_value   = money(net_gold_weight_g × rate_per_gram)
wastage       = money(metal_value × wastage_percent / 100)            # 0 if not configured
making_charge = per_gram : money(net_gold_weight_g × making_value)
                percent  : money(metal_value × making_value / 100)
                flat     : money(making_value)
                none     : 0
stone_value   = money(variant.stone_value or 0)
other_charges = money(variant.other_charges or 0)
```
### Fixed
```
product_value = money(variant.fixed_price)        # pre-tax, entered by admin
```
### Automatic discount (at most one per line — the largest for the customer)
| Kind | Effect |
|------|--------|
| `percent_off_making` | `money((making_charge + wastage) × p / 100)`, taken off making/wastage |
| `percent_off_price` | `money(pre_tax × p / 100)`, spread across all components |
| `flat_off_price` | `min(value, pre_tax)`, spread across all components |

### Tax
Tax is calculated **per component after discounts**, each with its configured rate:
`tax = Σ money(component_after_discount × rate / 100)`, where metal value and wastage use
`metal_percent`, making charges use `making_percent`, stones and other charges use `stones_percent`,
and the fixed-model product value uses `metal_percent`.

`unit_total = pre_tax − discount + tax`.

## 3. Line and order totals

```
line components = unit components × quantity
subtotal          = Σ line pre-tax values (before any discount)
automatic_disc    = Σ line automatic discounts
coupon_disc       = percent: money((subtotal − automatic_disc) × p / 100), capped at max_discount_amount
                    flat   : min(value, subtotal − automatic_disc)
discount_total    = automatic_disc + coupon_disc
taxable_total     = subtotal − discount_total
tax_total         = Σ line taxes (recomputed after coupon allocation) + shipping tax
shipping_total    = method fee, or 0 when (subtotal − discount_total) ≥ free_above
pre_round_total   = taxable_total + tax_total + shipping_total
grand_total       = pre_round_total rounded to the nearest whole rupee (ROUND_HALF_UP)
rounding_adjustment = grand_total − pre_round_total          (between −0.50 and +0.50)
```

**Coupon allocation:** the coupon amount is split across lines in proportion to each line's
taxable value, and inside a line across its components, using the *largest remainder* method at
paise precision, so the pieces always add up exactly to the coupon amount. Tax is then calculated
on the reduced component values. (Under Indian GST, discounts recorded on the invoice at the time of
supply reduce the taxable value — **to be confirmed by the owner's tax advisor**.)

## 4. Worked example (illustrative numbers only — not market data)

22K ring, net weight 4.000 g, illustrative rate ₹7,000.00/g, making 12% of metal value, no
wastage, no stones, tax 3% on everything, free shipping.

| Component | Calculation | Amount (₹) |
|-----------|-------------|-----------:|
| Metal value | 4.000 × 7,000.00 | 28,000.00 |
| Making charges | 12% × 28,000.00 | 3,360.00 |
| Pre-tax value | | 31,360.00 |
| GST (3%) | 3% × 28,000.00 + 3% × 3,360.00 | 940.80 |
| Unit total | | 32,300.80 |
| Rounding adjustment | to nearest rupee | +0.20 |
| **Grand total** | | **32,301.00** |

This exact case is a unit test (`test_worked_example_from_docs`).

## 5. When a price cannot be calculated
* A weight-based product whose purity has **no gold rate** is shown as "Price unavailable" and
  cannot be added to the cart or checked out.
* A fixed product without `fixed_price`, or a weight-based variant without `net_gold_weight_g`,
  fails validation in the admin and cannot be published.

## 6. Price-change policy (customer protection)
1. When an item is added to the cart, its current `unit_total` is stored as `accepted_unit_price`.
2. Every cart read recalculates prices.
   * **Increase** → the line is flagged `price_changed`, and checkout is blocked until the customer
     presses "Accept updated prices" (`POST /cart/accept-prices`).
   * **Decrease** → applied automatically. The customer sees an informational notice.
3. `POST /checkout/orders` requires `expected_total` — the grand total the customer saw on the
   review step. If the backend's fresh calculation differs by even ₹0.01, the order is **not**
   created and `409 PRICE_CHANGED` is returned with the new quote. The browser value is only a
   consent check and is never used as the price.
4. Once the order is created, all price components and inputs are frozen into `order_items` and
   `orders.pricing_context`, and the Razorpay amount equals `grand_total`. Later rate changes do not
   affect that order. If payment does not complete within the payment window (default 30 min),
   the order expires and a new checkout uses new prices.

## 7. Gold rate administration
* Rates are **append-only**. A new rate row with an `effective_from` takes over from that moment,
  and history is preserved for audits.
* `source_note` is required (e.g. "IBJA AM rate 14-Oct-2026" — whatever source the owner uses).
* `POST /admin/gold-rates/preview` shows the old vs new price of every affected active product before
  saving.
* A change larger than `gold_rate_max_change_percent` (default 5%) is rejected unless the request
  includes `confirm_large_change: true` (the UI shows an explicit confirmation dialog).
* Every rate change writes an audit-log entry.
* If the newest rate for a purity is older than `gold_rate_stale_after_hours` (default 36), the admin
  dashboard shows a warning. Optionally, `block_checkout_when_rate_stale` stops checkout of
  weight-based products.
* **No live gold-rate API is used.** No supposedly current market rate is hard-coded.

## 8. Listing price cache
Sorting and filtering by price in SQL needs a stored number. `products.price_from` (the lowest
active variant's `unit_total`) is a **cache** that is refreshed when a gold rate, product, variant,
discount or tax setting changes, and every 10 minutes by the background job (this catches discount
start/end times). Prices *displayed* on listing cards are computed live by the engine. The cache only
affects ordering and filter membership, never what anyone pays.

## 9. Audit snapshot on orders
`order_items.price_inputs` stores: gold rate id, rate per gram, purity, net weight, making type and
value, wastage %, tax rates, discount id/kind/value. `orders.pricing_context` stores the tax settings
and the engine version. Historical orders can therefore be re-explained exactly, even after products
or rates change.
