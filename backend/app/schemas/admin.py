"""Admin API requests/responses (operations: dashboard, orders, inventory, gold rates, customers,
audit). Money is serialised as strings; staff never send prices for orders."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.money import MoneyStr
from app.schemas.account import AddressOut
from app.schemas.common import StrictIn
from app.schemas.orders import OrderOut, OrderStatus, OrderSummaryOut, PaymentStatus

Purity = Literal["24K", "22K", "18K", "14K"]

# --------------------------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------------------------


class AdminOrderRowOut(BaseModel):
    reference: str
    created_at: datetime
    customer_name: str
    email: str
    status: OrderStatus
    status_label: str
    payment_status: PaymentStatus
    payment_status_label: str
    grand_total: MoneyStr
    item_count: int


class LowStockOut(BaseModel):
    sku: str
    product_name: str
    variant_label: str
    available: int
    threshold: int


class BestSellerOut(BaseModel):
    product_name: str
    product_slug: str
    quantity: int


class RateStatusOut(BaseModel):
    purity: Purity
    rate_per_gram: MoneyStr | None
    effective_from: datetime | None
    source_note: str | None
    age_hours: Decimal | None
    stale: bool


class DashboardOut(BaseModel):
    date_from: datetime
    date_to: datetime
    paid_orders: int
    paid_revenue: MoneyStr
    refunded: MoneyStr
    # Paid in the period minus refunds processed in the period.
    net_revenue: MoneyStr
    paid_orders_today: int
    pending_payment: int
    payment_review: int
    to_fulfil: int
    recent_orders: list[AdminOrderRowOut]
    review_orders: list[AdminOrderRowOut]
    low_stock: list[LowStockOut]
    best_sellers: list[BestSellerOut]
    gold_rates: list[RateStatusOut]


# --------------------------------------------------------------------------------------------
# Orders
# --------------------------------------------------------------------------------------------


class AdminOrderEventOut(BaseModel):
    kind: str
    title: str
    note: str | None
    from_status: str | None
    to_status: str | None
    actor_type: str
    customer_visible: bool
    created_at: datetime


class PaymentAttemptOut(BaseModel):
    provider: str
    provider_order_id: str
    provider_payment_id: str | None
    amount_paise: int
    status: str
    method: str | None
    error_description: str | None
    created_at: datetime


class AdminRefundOut(BaseModel):
    id: str
    amount: MoneyStr
    status: str
    reason: str
    provider_refund_id: str | None
    created_at: datetime


class AdminOrderOut(BaseModel):
    order: OrderOut
    customer_id: str | None
    events: list[AdminOrderEventOut]
    payment_attempts: list[PaymentAttemptOut]
    refunds: list[AdminRefundOut]
    refundable: MoneyStr
    allowed_actions: list[str]


class ShipIn(StrictIn):
    carrier: str = Field(min_length=2, max_length=80)
    tracking_number: str = Field(min_length=3, max_length=80)
    tracking_url: str | None = Field(default=None, max_length=500)

    @field_validator("tracking_url")
    @classmethod
    def _https(cls, value: str | None) -> str | None:
        if value and not value.startswith("https://"):
            raise ValueError("Use a full https:// tracking link.")
        return value or None


class ReasonIn(StrictIn):
    reason: str = Field(min_length=3, max_length=300)


class NoteIn(StrictIn):
    note: str = Field(min_length=1, max_length=500)


class ResolveReviewIn(StrictIn):
    decision: Literal["confirm", "refund"]
    note: str = Field(default="", max_length=300)


class RefundIn(StrictIn):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=3, max_length=300)


class OrderStatusAction(StrictIn):
    action: Literal["start_processing", "mark_delivered"]


# --------------------------------------------------------------------------------------------
# Inventory
# --------------------------------------------------------------------------------------------


class InventoryRowOut(BaseModel):
    variant_id: str
    sku: str
    product_name: str
    product_slug: str
    variant_label: str
    product_status: str
    on_hand: int
    reserved: int
    available: int
    low_stock_threshold: int
    stock_status: str


class AdjustStockIn(StrictIn):
    delta: int = Field(ge=-10_000, le=10_000)
    note: str = Field(min_length=3, max_length=300)

    @field_validator("delta")
    @classmethod
    def _non_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("Enter a number of pieces to add or remove.")
        return value


class ThresholdIn(StrictIn):
    low_stock_threshold: int = Field(ge=0, le=1000)


class MovementOut(BaseModel):
    created_at: datetime
    sku: str
    product_name: str
    delta_on_hand: int
    delta_reserved: int
    reason: str
    note: str | None
    order_reference: str | None
    actor_email: str | None


# --------------------------------------------------------------------------------------------
# Gold rates
# --------------------------------------------------------------------------------------------


class GoldRateOut(BaseModel):
    id: str
    purity: Purity
    rate_per_gram: MoneyStr
    effective_from: datetime
    source_note: str
    created_at: datetime


class GoldRatesOut(BaseModel):
    current: list[RateStatusOut]
    history: list[GoldRateOut]
    max_change_percent: Decimal
    stale_after_hours: int


class RatePreviewIn(StrictIn):
    purity: Purity
    rate_per_gram: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class PriceImpactOut(BaseModel):
    product_name: str
    product_slug: str
    sku: str
    variant_label: str
    old_price: MoneyStr | None
    new_price: MoneyStr


class RatePreviewOut(BaseModel):
    purity: Purity
    current_rate: MoneyStr | None
    new_rate: MoneyStr
    change_percent: Decimal | None
    needs_confirmation: bool
    max_change_percent: Decimal
    impacts: list[PriceImpactOut]


class CreateRateIn(RatePreviewIn):
    source_note: str = Field(min_length=3, max_length=300)
    effective_from: datetime | None = None
    confirm_large_change: bool = False


# --------------------------------------------------------------------------------------------
# Customers and audit
# --------------------------------------------------------------------------------------------


class CustomerRowOut(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str | None
    created_at: datetime
    is_active: bool
    email_verified: bool
    order_count: int
    paid_total: MoneyStr


class CustomerDetailOut(BaseModel):
    customer: CustomerRowOut
    addresses: list[AddressOut]
    orders: list[OrderSummaryOut]


class AuditLogOut(BaseModel):
    id: str
    created_at: datetime
    actor_email: str | None
    actor_role: str | None
    action: str
    entity_type: str
    entity_id: str | None
    changes: dict[str, Any]
    ip_address: str | None
