"""Pricing engine tests. The engine must match docs/architecture/PRICING_ENGINE.md exactly."""

from __future__ import annotations

import random
from decimal import Decimal as D

import pytest

from app.services.pricing import (
    CouponInput,
    DiscountInput,
    GoldRateInput,
    OrderLine,
    PriceUnavailable,
    ProductPricing,
    ShippingInput,
    TaxRates,
    VariantPricing,
    allocate,
    price_order,
    price_unit,
    unit_breakdown,
)

TAX_3 = TaxRates(metal=D("3"), making=D("3"), stones=D("3"), shipping=D("0"))
RATE_22K = GoldRateInput(id=None, purity="22K", rate_per_gram=D("7000.00"))


def weight_product(
    making_type: str = "percent",
    making_value: str = "12",
    wastage: str | None = None,
    purity: str = "22K",
) -> ProductPricing:
    return ProductPricing(
        pricing_model="weight_based",
        purity=purity,
        making_charge_type=making_type,
        making_charge_value=D(making_value),
        wastage_percent=D(wastage) if wastage else None,
    )


def variant(
    weight: str | None = "4.000", stones: str = "0", other: str = "0", fixed: str | None = None
) -> VariantPricing:
    return VariantPricing(
        net_gold_weight_g=D(weight) if weight else None,
        fixed_price=D(fixed) if fixed else None,
        stone_value=D(stones),
        other_charges=D(other),
    )


# ---------------------------------------------------------------- §4 worked example


def test_worked_example_from_docs() -> None:
    unit = price_unit(weight_product(), variant(), RATE_22K, TAX_3)
    assert unit.components == {"metal": D("28000.00"), "making": D("3360.00")}
    assert unit.pre_tax == D("31360.00")
    assert unit.tax == D("940.80")
    assert unit.total == D("32300.80")

    order = price_order([OrderLine(unit=unit, quantity=1)], TAX_3)
    assert order.rounding_adjustment == D("0.20")
    assert order.grand_total == D("32301.00")


# ---------------------------------------------------------------- making charges, wastage, extras


@pytest.mark.parametrize(
    ("making_type", "making_value", "expected_making"),
    [
        ("per_gram", "650", D("2600.00")),  # 4 g × 650
        ("percent", "12.5", D("3500.00")),  # 12.5% × 28000
        ("flat", "1999.99", D("1999.99")),
        ("none", "0", None),
    ],
)
def test_each_making_charge_type(
    making_type: str, making_value: str, expected_making: D | None
) -> None:
    unit = price_unit(weight_product(making_type, making_value), variant(), RATE_22K, TAX_3)
    assert unit.components.get("making") == expected_making


def test_wastage_applies_only_when_configured() -> None:
    without = price_unit(weight_product(), variant(), RATE_22K, TAX_3)
    with_wastage = price_unit(weight_product(wastage="2.5"), variant(), RATE_22K, TAX_3)
    assert "wastage" not in without.components
    assert with_wastage.components["wastage"] == D("700.00")  # 2.5% × 28000


def test_stones_and_other_charges_are_separate_components() -> None:
    unit = price_unit(weight_product(), variant(stones="12500.00", other="350.00"), RATE_22K, TAX_3)
    assert unit.components["stones"] == D("12500.00")
    assert unit.components["other"] == D("350.00")
    assert unit.tax == D("1326.30")  # 3% × (28000 + 3360 + 12500 + 350 = 44210)


def test_fixed_price_model_ignores_gold_rate() -> None:
    product = ProductPricing("fixed", "18K", "none", D("0"), None)
    unit = price_unit(product, variant(weight=None, fixed="15000.00"), None, TAX_3)
    assert unit.components == {"product": D("15000.00")}
    assert unit.total == D("15450.00")


def test_tax_rates_apply_per_component() -> None:
    tax = TaxRates(metal=D("3"), making=D("5"), stones=D("0.25"), shipping=D("18"))
    unit = price_unit(weight_product(), variant(stones="1000"), RATE_22K, tax)
    assert unit.tax_by_component == {
        "metal": D("840.00"),
        "making": D("168.00"),
        "stones": D("2.50"),
    }


def test_weight_and_rate_products_round_each_component_half_up() -> None:
    rate = GoldRateInput(None, "18K", D("5851.33"))
    unit = price_unit(weight_product(purity="18K"), variant(weight="1.235"), rate, TAX_3)
    # 1.235 × 5851.33 = 7226.39255 → 7226.39 ; making 12% = 867.1668 → 867.17
    assert unit.components["metal"] == D("7226.39")
    assert unit.components["making"] == D("867.17")


# ---------------------------------------------------------------- §5 cannot price


@pytest.mark.parametrize(
    ("product", "var", "rate", "reason"),
    [
        (weight_product(), variant(), None, "NO_GOLD_RATE"),
        (weight_product(), variant(weight=None), RATE_22K, "MISSING_WEIGHT"),
        (weight_product(purity="18K"), variant(), RATE_22K, "PURITY_MISMATCH"),
        (
            ProductPricing("fixed", "22K", "none", D(0), None),
            variant(),
            None,
            "MISSING_FIXED_PRICE",
        ),
    ],
)
def test_unpriceable_items_raise(
    product: ProductPricing, var: VariantPricing, rate: GoldRateInput | None, reason: str
) -> None:
    with pytest.raises(PriceUnavailable) as exc:
        price_unit(product, var, rate, TAX_3)
    assert exc.value.reason == reason


# ---------------------------------------------------------------- automatic discounts


def test_percent_off_making_only_reduces_making_and_its_tax() -> None:
    discount = DiscountInput(None, "20% off making", "percent_off_making", D("20"))
    unit = price_unit(weight_product(), variant(), RATE_22K, TAX_3, [discount])
    assert unit.discount_by_component == {"metal": D("0"), "making": D("672.00")}
    assert unit.tax_by_component["making"] == D("80.64")  # 3% × (3360 − 672)
    assert unit.total == D("31608.64")
    assert unit.total_before_discount == D("32300.80")


def test_percent_off_making_includes_wastage() -> None:
    discount = DiscountInput(None, "50% off making", "percent_off_making", D("50"))
    unit = price_unit(weight_product(wastage="2.5"), variant(), RATE_22K, TAX_3, [discount])
    # base = 3360 + 700 = 4060 → 2030, split proportionally
    assert unit.discount_amount == D("2030.00")
    assert unit.discount_by_component["making"] + unit.discount_by_component["wastage"] == D(
        "2030.00"
    )


def test_flat_discount_never_exceeds_price() -> None:
    discount = DiscountInput(None, "Huge", "flat_off_price", D("999999"))
    unit = price_unit(weight_product(), variant(), RATE_22K, TAX_3, [discount])
    assert unit.discount_amount == unit.pre_tax
    assert unit.total == D("0.00")


def test_best_discount_for_customer_is_chosen_and_only_one_applies() -> None:
    small = DiscountInput(None, "5% off", "percent_off_price", D("5"))  # 1568.00
    big = DiscountInput(None, "₹2000 off", "flat_off_price", D("2000"))  # 2000.00
    making = DiscountInput(None, "10% making", "percent_off_making", D("10"))  # 336.00
    unit = price_unit(weight_product(), variant(), RATE_22K, TAX_3, [small, big, making])
    assert unit.discount is big
    assert unit.discount_amount == D("2000.00")


def test_unit_breakdown_rows_sum_to_total() -> None:
    discount = DiscountInput(None, "5% off", "percent_off_price", D("5"))
    unit = price_unit(
        weight_product(wastage="1"), variant(stones="500"), RATE_22K, TAX_3, [discount]
    )
    rows = unit_breakdown(unit)
    assert rows[-1]["key"] == "total"
    assert sum(r["amount"] for r in rows[:-1]) == rows[-1]["amount"]
    assert rows[0]["label"] == "Gold value (22K)"


# ---------------------------------------------------------------- allocation


@pytest.mark.parametrize(
    ("amount", "weights", "expected"),
    [
        (D("100.00"), [D(1), D(1), D(1)], [D("33.34"), D("33.33"), D("33.33")]),
        (D("0.01"), [D(5), D(5)], [D("0.01"), D("0.00")]),
        (D("10.00"), [D(0), D(0)], [D("10.00"), D("0.00")]),
        (D("0"), [D(3), D(1)], [D("0"), D("0")]),
    ],
)
def test_allocate_examples(amount: D, weights: list[D], expected: list[D]) -> None:
    assert allocate(amount, weights) == expected


def test_allocate_always_sums_exactly() -> None:
    rng = random.Random(42)
    for _ in range(500):
        weights = [D(rng.randint(0, 100000)) / 100 for _ in range(rng.randint(1, 6))]
        amount = D(rng.randint(0, 5_000_000)) / 100
        parts = allocate(amount, weights)
        assert sum(parts) == amount
        assert all(p >= 0 for p in parts)


# ---------------------------------------------------------------- order level


def _unit(weight: str = "4.000") -> object:
    return price_unit(weight_product(), variant(weight=weight), RATE_22K, TAX_3)


def test_order_with_quantity_multiplies_lines() -> None:
    unit = price_unit(weight_product(), variant(), RATE_22K, TAX_3)
    order = price_order([OrderLine(unit=unit, quantity=2)], TAX_3)
    assert order.subtotal == D("62720.00")
    assert order.items_tax == D("1881.60")
    assert order.grand_total == D("64602.00")
    assert order.rounding_adjustment == D("0.40")


def test_percent_coupon_with_cap_and_exact_allocation() -> None:
    a = price_unit(weight_product(), variant(weight="4.000"), RATE_22K, TAX_3)
    b = price_unit(weight_product(), variant(weight="2.333"), RATE_22K, TAX_3)
    coupon = CouponInput("WELCOME5", "percent", D("5"), max_discount_amount=D("1500"))
    order = price_order([OrderLine(a, 1, "a"), OrderLine(b, 3, "b")], TAX_3, coupon=coupon)
    assert order.coupon_discount == D("1500.00")  # capped (5% would be more)
    assert sum(sum(lp.coupon_discount.values()) for lp in order.lines) == D("1500.00")
    assert order.taxable_total == order.subtotal - order.discount_total
    # tax is computed on discounted values
    assert order.items_tax == sum(lp.tax for lp in order.lines)


def test_flat_coupon_limited_to_eligible_amount() -> None:
    unit = price_unit(
        ProductPricing("fixed", "18K", "none", D(0), None), variant(fixed="500.00"), None, TAX_3
    )
    order = price_order([OrderLine(unit, 1)], TAX_3, coupon=CouponInput("BIG", "flat", D("800")))
    assert order.coupon_discount == D("500.00")
    assert order.grand_total == D("0.00")


def test_coupon_minimum_order_not_met() -> None:
    unit = price_unit(weight_product(), variant(), RATE_22K, TAX_3)
    coupon = CouponInput("MIN", "percent", D("5"), min_order_amount=D("50000"))
    order = price_order([OrderLine(unit, 1)], TAX_3, coupon=coupon)
    assert order.coupon_error == "MIN_ORDER_NOT_MET"
    assert order.coupon_discount == D("0")
    assert order.coupon_code is None


def test_coupon_applies_after_automatic_discount() -> None:
    discount = DiscountInput(None, "₹1360 off", "flat_off_price", D("1360"))
    unit = price_unit(weight_product(), variant(), RATE_22K, TAX_3, [discount])
    order = price_order([OrderLine(unit, 1)], TAX_3, coupon=CouponInput("P10", "percent", D("10")))
    assert order.automatic_discount == D("1360.00")
    assert order.coupon_discount == D("3000.00")  # 10% × (31360 − 1360)
    assert order.taxable_total == D("27000.00")
    assert order.items_tax == D("810.00")


def test_shipping_fee_and_free_threshold() -> None:
    unit = price_unit(weight_product(), variant(), RATE_22K, TAX_3)
    paid = price_order(
        [OrderLine(unit, 1)], TAX_3, shipping=ShippingInput("express", "Express", D("499"), None)
    )
    free = price_order(
        [OrderLine(unit, 1)],
        TAX_3,
        shipping=ShippingInput("std", "Standard", D("299"), free_above=D("25000")),
    )
    assert paid.shipping_fee == D("499.00")
    assert paid.grand_total == D("32800.00")  # 32300.80 + 499 = 32799.80 → 32800
    assert free.shipping_fee == D("0.00")


def test_shipping_tax_uses_shipping_rate() -> None:
    tax = TaxRates(D("3"), D("3"), D("3"), shipping=D("18"))
    unit = price_unit(weight_product(), variant(), RATE_22K, tax)
    order = price_order([OrderLine(unit, 1)], tax, shipping=ShippingInput("x", "X", D("100"), None))
    assert order.shipping_tax == D("18.00")
    assert order.tax_total == order.items_tax + D("18.00")


@pytest.mark.parametrize(
    ("fixed", "expected_total", "expected_rounding"),
    [
        ("100.00", "103.00", "0.00"),  # tax 3.00 → 103.00
        ("100.49", "104.00", "0.50"),  # tax 3.0147→3.01 → 103.50 → half-up to 104
        ("100.48", "103.00", "-0.49"),  # tax 3.0144→3.01 → 103.49 → 103
    ],
)
def test_grand_total_rounds_half_up_to_rupee(
    fixed: str, expected_total: str, expected_rounding: str
) -> None:
    unit = price_unit(
        ProductPricing("fixed", "18K", "none", D(0), None), variant(fixed=fixed), None, TAX_3
    )
    order = price_order([OrderLine(unit, 1)], TAX_3)
    assert order.grand_total == D(expected_total)
    assert order.rounding_adjustment == D(expected_rounding)
    assert order.pre_round_total + order.rounding_adjustment == order.grand_total


def test_empty_order_totals_zero() -> None:
    order = price_order([], TAX_3)
    assert order.grand_total == D("0")
    assert order.rounding_adjustment == D("0")


def test_order_breakdown_rows_sum_to_total() -> None:
    discount = DiscountInput(None, "10% making", "percent_off_making", D("10"))
    unit = price_unit(
        weight_product(wastage="2"), variant(stones="999.99"), RATE_22K, TAX_3, [discount]
    )
    order = price_order(
        [OrderLine(unit, 2)],
        TaxRates(D("3"), D("3"), D("3"), D("18")),
        coupon=CouponInput("C", "percent", D("3")),
        shipping=ShippingInput("x", "X", D("149"), None),
    )
    rows = order.breakdown
    assert rows[-1]["key"] == "total"
    assert sum(r["amount"] for r in rows[:-1]) == rows[-1]["amount"]


def test_no_floats_anywhere_in_results() -> None:
    unit = price_unit(weight_product(wastage="1.5"), variant(stones="10"), RATE_22K, TAX_3)
    order = price_order([OrderLine(unit, 3)], TAX_3, coupon=CouponInput("C", "percent", D("7")))
    values = [order.grand_total, order.items_tax, order.rounding_adjustment, unit.total]
    values += [v for lp in order.lines for v in lp.tax_by_component.values()]
    assert all(isinstance(v, D) for v in values)
