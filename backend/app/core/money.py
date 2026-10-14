"""Money helpers. Money is always Decimal (never float) and serialised as a 2-decimal string."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

PAISE = Decimal("0.01")
RUPEE = Decimal("1")
ZERO = Decimal("0.00")
CURRENCY = "INR"


def money(value: Decimal | int | str) -> Decimal:
    """Round to paise (2 dp) with ROUND_HALF_UP. Floats are rejected on purpose."""
    if isinstance(value, float):
        raise TypeError("Use Decimal or str for money, never float")
    return Decimal(value).quantize(PAISE, rounding=ROUND_HALF_UP)


def round_to_rupee(value: Decimal) -> Decimal:
    return value.quantize(RUPEE, rounding=ROUND_HALF_UP).quantize(PAISE)


def to_paise(value: Decimal) -> int:
    """Convert a rupee amount (2 dp) to integer paise for payment providers."""
    paise = money(value) * 100
    if paise != paise.to_integral_value():
        raise ValueError("Amount has more than 2 decimal places")
    return int(paise)


def _serialise(value: Decimal) -> str:
    return f"{money(value):.2f}"


# Output type: Decimal internally, "1234.50" in JSON.
MoneyStr = Annotated[Decimal, PlainSerializer(_serialise, return_type=str, when_used="json")]

# Input types for admin-entered amounts.
MoneyIn = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PercentIn = Annotated[Decimal, Field(ge=0, le=100, max_digits=6, decimal_places=3)]
WeightIn = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=3)]


def format_inr(value: Decimal) -> str:
    """₹ with Indian digit grouping for messages: 105150.33 → "₹1,05,150.33", 13287 → "₹13,287"."""
    amount = money(value)
    sign = "-" if amount < 0 else ""
    whole, _, paise = f"{abs(amount):.2f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    grouped = ",".join([*groups, tail]) if groups else tail
    return f"{sign}₹{grouped}" + ("" if paise == "00" else f".{paise}")
