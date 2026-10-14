from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.money import money, round_to_rupee, to_paise


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1.005", "1.01"), ("1.004", "1.00"), ("2.675", "2.68"), ("-1.005", "-1.01"), (5, "5.00")],
)
def test_money_rounds_half_up_to_paise(raw: str | int, expected: str) -> None:
    assert money(raw) == Decimal(expected)


def test_money_rejects_floats() -> None:
    with pytest.raises(TypeError):
        money(1.1)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("32300.80", "32301.00"), ("32300.50", "32301.00"), ("32300.49", "32300.00")],
)
def test_round_to_rupee(raw: str, expected: str) -> None:
    assert round_to_rupee(Decimal(raw)) == Decimal(expected)


def test_to_paise() -> None:
    assert to_paise(Decimal("32301.00")) == 3230100
    assert to_paise(Decimal("0.01")) == 1


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("105150.33", "₹1,05,150.33"),
        ("13287.00", "₹13,287"),
        ("999", "₹999"),
        ("1000", "₹1,000"),
        ("12345678.9", "₹1,23,45,678.90"),
        ("-191.40", "-₹191.40"),
    ],
)
def test_format_inr_uses_indian_grouping(raw: str, expected: str) -> None:
    from app.core.money import format_inr

    assert format_inr(Decimal(raw)) == expected
