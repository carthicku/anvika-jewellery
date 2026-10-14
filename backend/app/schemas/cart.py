"""Cart requests and responses. All amounts are calculated by the backend pricing engine."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.core.money import MoneyStr
from app.schemas.catalogue import ImageOut, PriceRowOut, StockStatusOut
from app.schemas.common import StrictIn

LineIssue = Literal["unavailable", "price_unavailable", "out_of_stock", "insufficient_stock"]


class AddToCartIn(StrictIn):
    variant_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=10)


class UpdateCartItemIn(StrictIn):
    quantity: int = Field(ge=1, le=10)


class CouponIn(StrictIn):
    code: str = Field(min_length=2, max_length=40)


class CartLineOut(BaseModel):
    id: str
    product_slug: str
    product_name: str
    variant_id: str
    variant_label: str
    size: str | None
    sku: str
    purity: str
    image: ImageOut | None
    quantity: int
    # How many the customer may choose (stock and the per-line limit of 10).
    max_quantity: int
    stock_status: StockStatusOut
    unit_price: MoneyStr | None
    accepted_unit_price: MoneyStr
    price_change: Literal["increased", "decreased"] | None
    line_total: MoneyStr | None
    issue: LineIssue | None


class CartTotalsOut(BaseModel):
    subtotal: MoneyStr
    automatic_discount: MoneyStr
    coupon_discount: MoneyStr
    tax_total: MoneyStr
    shipping_fee: MoneyStr
    shipping_label: str | None
    free_shipping_above: MoneyStr | None
    rounding_adjustment: MoneyStr
    grand_total: MoneyStr
    breakdown: list[PriceRowOut]


class CouponStateOut(BaseModel):
    code: str
    applied: bool
    message: str | None


class CartOut(BaseModel):
    lines: list[CartLineOut]
    item_count: int
    totals: CartTotalsOut | None
    coupon: CouponStateOut | None
    can_checkout: bool
    # Why checkout is blocked (shown to the customer), e.g. a price increase to accept.
    blocking_issues: list[str]
    notices: list[str]
