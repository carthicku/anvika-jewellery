"""Gold pricing engine — pure functions, no database access.

The specification is docs/architecture/PRICING_ENGINE.md; section numbers below refer to it.
Every amount is a Decimal rounded to paise with ROUND_HALF_UP via `money()`. Floats are never used.

Main entry points:
    price_unit(product, variant, rate, tax, discounts)   -> UnitPrice      (§2)
    price_order(lines, tax, coupon=None, shipping=None)   -> OrderPrice     (§3)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, Decimal
from typing import Any, Literal
from uuid import UUID

from app.core.money import ZERO, money, round_to_rupee

ENGINE_VERSION = "1"
HUNDRED = Decimal(100)

# Component keys, in display order, and the tax-rate group each belongs to (§2 "Tax").
COMPONENT_ORDER = ("metal", "wastage", "making", "stones", "other", "product")
COMPONENT_LABELS = {
    "metal": "Gold value",
    "wastage": "Wastage",
    "making": "Making charges",
    "stones": "Stones",
    "other": "Other charges",
    "product": "Product price",
}
TAX_GROUP = {
    "metal": "metal",
    "wastage": "metal",
    "making": "making",
    "stones": "stones",
    "other": "stones",
    "product": "metal",
}

UnavailableReason = Literal[
    "NO_GOLD_RATE", "MISSING_WEIGHT", "MISSING_FIXED_PRICE", "PURITY_MISMATCH"
]


class PriceUnavailable(Exception):
    """The item cannot be priced, so it must not be sold (§5)."""

    def __init__(self, reason: UnavailableReason) -> None:
        self.reason = reason
        super().__init__(reason)


# --------------------------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TaxRates:
    """Percentages, e.g. Decimal("3.00") for 3%. Owner-configured (placeholders until CA review)."""

    metal: Decimal
    making: Decimal
    stones: Decimal
    shipping: Decimal

    def for_component(self, key: str) -> Decimal:
        group = TAX_GROUP[key]
        rate: Decimal = getattr(self, group)
        return rate

    def as_dict(self) -> dict[str, str]:
        return {k: str(getattr(self, k)) for k in ("metal", "making", "stones", "shipping")}


@dataclass(frozen=True)
class ProductPricing:
    pricing_model: str  # "fixed" | "weight_based"
    purity: str
    making_charge_type: str  # "per_gram" | "percent" | "flat" | "none"
    making_charge_value: Decimal
    wastage_percent: Decimal | None


@dataclass(frozen=True)
class VariantPricing:
    net_gold_weight_g: Decimal | None
    fixed_price: Decimal | None
    stone_value: Decimal
    other_charges: Decimal


@dataclass(frozen=True)
class GoldRateInput:
    id: UUID | None
    purity: str
    rate_per_gram: Decimal


@dataclass(frozen=True)
class DiscountInput:
    id: UUID | None
    name: str
    kind: str  # "percent_off_making" | "percent_off_price" | "flat_off_price"
    value: Decimal


@dataclass(frozen=True)
class CouponInput:
    code: str
    kind: str  # "percent" | "flat"
    value: Decimal
    max_discount_amount: Decimal | None = None
    min_order_amount: Decimal | None = None


@dataclass(frozen=True)
class ShippingInput:
    code: str
    name: str
    fee: Decimal
    free_above: Decimal | None


# --------------------------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------------------------


@dataclass
class UnitPrice:
    """Price of ONE piece of a variant, after its automatic discount (no coupon)."""

    components: dict[str, Decimal]  # before discount
    discount_by_component: dict[str, Decimal]
    discount: DiscountInput | None
    tax_by_component: dict[str, Decimal]
    tax_rates: TaxRates
    rate: GoldRateInput | None
    inputs: dict[str, Any]

    @property
    def pre_tax(self) -> Decimal:
        return sum(self.components.values(), ZERO)

    @property
    def discount_amount(self) -> Decimal:
        return sum(self.discount_by_component.values(), ZERO)

    @property
    def tax(self) -> Decimal:
        return sum(self.tax_by_component.values(), ZERO)

    @property
    def total(self) -> Decimal:
        return self.pre_tax - self.discount_amount + self.tax

    @property
    def total_before_discount(self) -> Decimal:
        """What the piece would cost without the automatic discount (for strike-through display)."""
        if not self.discount:
            return self.total
        full_tax = sum(
            (
                money(v * self.tax_rates.for_component(k) / HUNDRED)
                for k, v in self.components.items()
            ),
            ZERO,
        )
        return self.pre_tax + full_tax


@dataclass
class OrderLine:
    unit: UnitPrice
    quantity: int
    key: str = ""  # caller's identifier (e.g. cart item id)


@dataclass
class LinePrice:
    key: str
    quantity: int
    unit_total: Decimal
    components: dict[str, Decimal]  # line amounts before any discount
    automatic_discount: dict[str, Decimal]
    coupon_discount: dict[str, Decimal]
    tax_by_component: dict[str, Decimal]

    @property
    def pre_tax(self) -> Decimal:
        return sum(self.components.values(), ZERO)

    @property
    def discount(self) -> Decimal:
        return sum(self.automatic_discount.values(), ZERO) + sum(
            self.coupon_discount.values(), ZERO
        )

    @property
    def taxable_value(self) -> Decimal:
        return self.pre_tax - self.discount

    @property
    def tax(self) -> Decimal:
        return sum(self.tax_by_component.values(), ZERO)

    @property
    def total(self) -> Decimal:
        return self.taxable_value + self.tax


@dataclass
class OrderPrice:
    lines: list[LinePrice]
    subtotal: Decimal
    automatic_discount: Decimal
    coupon_discount: Decimal
    coupon_code: str | None
    coupon_error: str | None
    taxable_total: Decimal
    items_tax: Decimal
    shipping_fee: Decimal
    shipping_tax: Decimal
    shipping_code: str | None
    pre_round_total: Decimal
    grand_total: Decimal
    rounding_adjustment: Decimal
    tax_rates: TaxRates
    engine_version: str = ENGINE_VERSION
    breakdown: list[dict[str, Any]] = field(default_factory=list)

    @property
    def discount_total(self) -> Decimal:
        return self.automatic_discount + self.coupon_discount

    @property
    def tax_total(self) -> Decimal:
        return self.items_tax + self.shipping_tax


# --------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------


def allocate(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Split `amount` into parts proportional to `weights` that sum EXACTLY to `amount`.

    Works in whole paise using the largest-remainder method (§3 "Coupon allocation"); ties go to
    the earlier position so results are deterministic.
    """
    if not weights:
        return []
    total_paise = int(money(amount) * 100)
    weight_sum = sum(weights, ZERO)
    if total_paise == 0:
        return [ZERO for _ in weights]
    if weight_sum <= 0:
        parts = [0] * len(weights)
        parts[0] = total_paise
        return [Decimal(p) / 100 for p in parts]

    exact = [Decimal(total_paise) * w / weight_sum for w in weights]
    floors = [int(e.to_integral_value(rounding=ROUND_FLOOR)) for e in exact]
    remainder = total_paise - sum(floors)
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - floors[i]), i))
    for i in order[:remainder]:
        floors[i] += 1
    return [money(Decimal(p) / 100) for p in floors]


def _allocate_over(
    amount: Decimal, values: dict[str, Decimal], keys: Sequence[str] | None = None
) -> dict[str, Decimal]:
    keys = [k for k in (keys or list(values)) if k in values]
    parts = allocate(amount, [values[k] for k in keys])
    result = dict.fromkeys(values, ZERO)
    result.update(zip(keys, parts, strict=True))
    return result


def _tax(values: dict[str, Decimal], rates: TaxRates) -> dict[str, Decimal]:
    return {k: money(v * rates.for_component(k) / HUNDRED) for k, v in values.items()}


# --------------------------------------------------------------------------------------------
# §2 Unit price
# --------------------------------------------------------------------------------------------


def base_components(
    product: ProductPricing, variant: VariantPricing, rate: GoldRateInput | None
) -> dict[str, Decimal]:
    """Pre-tax, pre-discount components for one piece. Raises PriceUnavailable (§5)."""
    if product.pricing_model == "fixed":
        if variant.fixed_price is None:
            raise PriceUnavailable("MISSING_FIXED_PRICE")
        return {"product": money(variant.fixed_price)}

    if rate is None:
        raise PriceUnavailable("NO_GOLD_RATE")
    if rate.purity != product.purity:
        raise PriceUnavailable("PURITY_MISMATCH")
    weight = variant.net_gold_weight_g
    if weight is None or weight <= 0:
        raise PriceUnavailable("MISSING_WEIGHT")

    metal = money(weight * rate.rate_per_gram)
    wastage = money(metal * product.wastage_percent / HUNDRED) if product.wastage_percent else ZERO
    value = product.making_charge_value
    match product.making_charge_type:
        case "per_gram":
            making = money(weight * value)
        case "percent":
            making = money(metal * value / HUNDRED)
        case "flat":
            making = money(value)
        case _:
            making = ZERO

    components = {"metal": metal}
    if wastage:
        components["wastage"] = wastage
    if making:
        components["making"] = making
    if variant.stone_value:
        components["stones"] = money(variant.stone_value)
    if variant.other_charges:
        components["other"] = money(variant.other_charges)
    return components


def discount_allocation(
    components: dict[str, Decimal], discount: DiscountInput
) -> dict[str, Decimal]:
    """How much of `discount` comes off each component (§2 "Automatic discount")."""
    pre_tax = sum(components.values(), ZERO)
    if discount.kind == "percent_off_making":
        making_keys = [k for k in ("making", "wastage") if k in components]
        base = sum((components[k] for k in making_keys), ZERO)
        amount = money(base * discount.value / HUNDRED)
        return _allocate_over(amount, components, making_keys)
    if discount.kind == "percent_off_price":
        amount = money(pre_tax * discount.value / HUNDRED)
    elif discount.kind == "flat_off_price":
        amount = min(money(discount.value), pre_tax)
    else:  # pragma: no cover - guarded by DB CHECK constraint
        raise ValueError(f"Unknown discount kind {discount.kind}")
    return _allocate_over(amount, components)


def best_discount(
    components: dict[str, Decimal], discounts: list[DiscountInput]
) -> tuple[DiscountInput | None, dict[str, Decimal]]:
    """Pick the single discount that saves the customer the most (ties: first in the list)."""
    best: DiscountInput | None = None
    best_alloc = dict.fromkeys(components, ZERO)
    best_amount = ZERO
    for discount in discounts:
        alloc = discount_allocation(components, discount)
        amount = sum(alloc.values(), ZERO)
        if amount > best_amount:
            best, best_alloc, best_amount = discount, alloc, amount
    return best, best_alloc


def price_unit(
    product: ProductPricing,
    variant: VariantPricing,
    rate: GoldRateInput | None,
    tax: TaxRates,
    discounts: list[DiscountInput] | None = None,
) -> UnitPrice:
    components = base_components(product, variant, rate)
    discount, discount_alloc = best_discount(components, discounts or [])
    after_discount = {k: v - discount_alloc[k] for k, v in components.items()}
    inputs: dict[str, Any] = {
        "engine_version": ENGINE_VERSION,
        "pricing_model": product.pricing_model,
        "purity": product.purity,
        "making_charge_type": product.making_charge_type,
        "making_charge_value": str(product.making_charge_value),
        "wastage_percent": str(product.wastage_percent) if product.wastage_percent else None,
        "net_gold_weight_g": str(variant.net_gold_weight_g) if variant.net_gold_weight_g else None,
        "fixed_price": str(variant.fixed_price) if variant.fixed_price is not None else None,
        "stone_value": str(variant.stone_value),
        "other_charges": str(variant.other_charges),
        "gold_rate_id": str(rate.id) if rate and rate.id else None,
        "gold_rate_per_gram": str(rate.rate_per_gram) if rate else None,
        "tax_rates": tax.as_dict(),
        "discount": (
            {
                "id": str(discount.id),
                "name": discount.name,
                "kind": discount.kind,
                "value": str(discount.value),
            }
            if discount
            else None
        ),
    }
    return UnitPrice(
        components=components,
        discount_by_component=discount_alloc,
        discount=discount,
        tax_by_component=_tax(after_discount, tax),
        tax_rates=tax,
        rate=rate if product.pricing_model == "weight_based" else None,
        inputs=inputs,
    )


# --------------------------------------------------------------------------------------------
# §3 Lines and order totals
# --------------------------------------------------------------------------------------------


def coupon_amount(coupon: CouponInput, eligible_base: Decimal) -> tuple[Decimal, str | None]:
    """Coupon value on the pre-tax subtotal after automatic discounts -> (amount, error)."""
    if eligible_base <= 0:
        return ZERO, "NOTHING_TO_DISCOUNT"
    if coupon.min_order_amount is not None and eligible_base < coupon.min_order_amount:
        return ZERO, "MIN_ORDER_NOT_MET"
    if coupon.kind == "percent":
        amount = money(eligible_base * coupon.value / HUNDRED)
        if coupon.max_discount_amount is not None:
            amount = min(amount, money(coupon.max_discount_amount))
    else:
        amount = min(money(coupon.value), eligible_base)
    return amount, None


def price_order(
    lines: list[OrderLine],
    tax: TaxRates,
    coupon: CouponInput | None = None,
    shipping: ShippingInput | None = None,
) -> OrderPrice:
    # 1. Line amounts before coupon.
    priced: list[LinePrice] = []
    for line in lines:
        q = Decimal(line.quantity)
        priced.append(
            LinePrice(
                key=line.key,
                quantity=line.quantity,
                unit_total=line.unit.total,
                components={k: v * q for k, v in line.unit.components.items()},
                automatic_discount={k: v * q for k, v in line.unit.discount_by_component.items()},
                coupon_discount=dict.fromkeys(line.unit.components, ZERO),
                tax_by_component={},
            )
        )

    subtotal = sum((lp.pre_tax for lp in priced), ZERO)
    automatic = sum((sum(lp.automatic_discount.values(), ZERO) for lp in priced), ZERO)
    eligible = subtotal - automatic

    # 2. Coupon, allocated across lines, then across each line's components.
    coupon_total, coupon_error = (ZERO, None)
    if coupon is not None:
        coupon_total, coupon_error = coupon_amount(coupon, eligible)
    if coupon_total > 0:
        line_bases = [lp.pre_tax - sum(lp.automatic_discount.values(), ZERO) for lp in priced]
        for lp, share in zip(priced, allocate(coupon_total, line_bases), strict=True):
            remaining = {k: v - lp.automatic_discount[k] for k, v in lp.components.items()}
            lp.coupon_discount = _allocate_over(share, remaining)

    # 3. Tax per component on the fully discounted line values.
    for lp in priced:
        after = {
            k: v - lp.automatic_discount[k] - lp.coupon_discount[k]
            for k, v in lp.components.items()
        }
        lp.tax_by_component = _tax(after, tax)

    taxable_total = sum((lp.taxable_value for lp in priced), ZERO)
    items_tax = sum((lp.tax for lp in priced), ZERO)

    # 4. Shipping (free above threshold, compared with the discounted pre-tax value).
    shipping_fee = ZERO
    if shipping is not None:
        free = shipping.free_above is not None and taxable_total >= shipping.free_above
        shipping_fee = ZERO if free else money(shipping.fee)
    shipping_tax = money(shipping_fee * tax.shipping / HUNDRED)

    # 5. Rounding to the rupee.
    pre_round = taxable_total + items_tax + shipping_fee + shipping_tax
    grand_total = round_to_rupee(pre_round) if priced else ZERO
    rounding = grand_total - pre_round if priced else ZERO

    order = OrderPrice(
        lines=priced,
        subtotal=subtotal,
        automatic_discount=automatic,
        coupon_discount=coupon_total,
        coupon_code=coupon.code if coupon and coupon_total > 0 else None,
        coupon_error=coupon_error,
        taxable_total=taxable_total,
        items_tax=items_tax,
        shipping_fee=shipping_fee,
        shipping_tax=shipping_tax,
        shipping_code=shipping.code if shipping else None,
        pre_round_total=pre_round,
        grand_total=grand_total,
        rounding_adjustment=rounding,
        tax_rates=tax,
    )
    order.breakdown = order_breakdown(order)
    return order


# --------------------------------------------------------------------------------------------
# Display rows (the frontend renders these; it never calculates)
# --------------------------------------------------------------------------------------------


def unit_breakdown(unit: UnitPrice) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in COMPONENT_ORDER:
        if key in unit.components:
            label = COMPONENT_LABELS[key]
            if key == "metal" and unit.rate:
                label = f"Gold value ({unit.rate.purity})"
            rows.append({"key": key, "label": label, "amount": unit.components[key]})
    if unit.discount_amount:
        rows.append(
            {
                "key": "discount",
                "label": unit.discount.name if unit.discount else "Discount",
                "amount": -unit.discount_amount,
            }
        )
    rows.append({"key": "tax", "label": "GST", "amount": unit.tax})
    rows.append({"key": "total", "label": "Total", "amount": unit.total})
    return rows


def order_breakdown(order: OrderPrice) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {"key": "subtotal", "label": "Items (before tax)", "amount": order.subtotal}
    ]
    if order.automatic_discount:
        rows.append(
            {"key": "automatic_discount", "label": "Offers", "amount": -order.automatic_discount}
        )
    if order.coupon_discount:
        rows.append(
            {
                "key": "coupon_discount",
                "label": f"Coupon {order.coupon_code}",
                "amount": -order.coupon_discount,
            }
        )
    rows.append({"key": "tax", "label": "GST", "amount": order.items_tax})
    if order.shipping_code is not None:
        rows.append({"key": "shipping", "label": "Shipping", "amount": order.shipping_fee})
        if order.shipping_tax:
            rows.append(
                {"key": "shipping_tax", "label": "GST on shipping", "amount": order.shipping_tax}
            )
    if order.rounding_adjustment:
        rows.append(
            {"key": "rounding", "label": "Rounding adjustment", "amount": order.rounding_adjustment}
        )
    rows.append({"key": "total", "label": "Total", "amount": order.grand_total})
    return rows
