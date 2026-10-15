"""Checkout, payment and order requests/responses.

The browser never sends prices. `expected_total` is only the customer's consent to the total they
were shown; the backend recalculates everything and refuses the order if it differs.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.money import MoneyStr
from app.schemas.account import AddressFieldsIn
from app.schemas.cart import CartOut
from app.schemas.catalogue import ImageOut, PriceRowOut
from app.schemas.common import StrictIn
from app.services.shipping import ShippingOptionOut

OrderStatus = Literal[
    "pending_payment",
    "confirmed",
    "processing",
    "shipped",
    "delivered",
    "cancelled",
    "expired",
    "payment_review",
    "returned",
]
PaymentStatus = Literal[
    "unpaid", "authorized", "paid", "failed", "refund_pending", "partially_refunded", "refunded"
]

# --------------------------------------------------------------------------------------------
# Checkout
# --------------------------------------------------------------------------------------------


class CheckoutQuoteIn(StrictIn):
    pincode: str = Field(max_length=10)
    shipping_method: str | None = Field(default=None, max_length=40)


class CheckoutQuoteOut(BaseModel):
    cart: CartOut
    pincode: str
    serviceable: bool
    message: str | None
    shipping_options: list[ShippingOptionOut]
    shipping_method: str | None


class CreateOrderIn(StrictIn):
    email: EmailStr | None = Field(
        default=None, description="Required for guests; signed-in customers use their account email"
    )
    shipping_address: AddressFieldsIn
    billing_address: AddressFieldsIn | None = Field(
        default=None, description="Omit when billing is the same as shipping"
    )
    shipping_method: str = Field(max_length=40)
    expected_total: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    terms_accepted: bool
    customer_note: str | None = Field(default=None, max_length=500)


class PaymentPrefillOut(BaseModel):
    name: str
    email: str
    contact: str


class PaymentSessionOut(BaseModel):
    """What the browser needs to open the payment pop-up. Contains no secrets."""

    provider: Literal["razorpay", "simulator"]
    key_id: str
    provider_order_id: str
    amount_paise: int
    currency: str
    store_name: str
    description: str
    prefill: PaymentPrefillOut


# --------------------------------------------------------------------------------------------
# Orders
# --------------------------------------------------------------------------------------------


class OrderAddressOut(BaseModel):
    full_name: str
    phone: str
    line1: str
    line2: str | None = None
    landmark: str | None = None
    city: str
    state: str
    pincode: str
    country: str = "IN"


class OrderShippingMethodOut(BaseModel):
    code: str
    name: str
    min_days: int
    max_days: int
    estimated_from: date
    estimated_to: date


class OrderItemOut(BaseModel):
    product_name: str
    product_slug: str
    variant_label: str
    sku: str
    purity: str
    image: ImageOut | None
    quantity: int
    unit_price: MoneyStr
    line_discount: MoneyStr
    line_tax: MoneyStr
    line_total: MoneyStr


class OrderTotalsOut(BaseModel):
    subtotal: MoneyStr
    automatic_discount: MoneyStr
    coupon_discount: MoneyStr
    tax_total: MoneyStr
    shipping_total: MoneyStr
    rounding_adjustment: MoneyStr
    grand_total: MoneyStr
    breakdown: list[PriceRowOut]


class OrderEventOut(BaseModel):
    kind: str
    title: str
    note: str | None
    created_at: datetime


class ShipmentOut(BaseModel):
    carrier: str
    tracking_number: str
    tracking_url: str | None
    status: str
    shipped_at: datetime | None
    delivered_at: datetime | None


class RefundOut(BaseModel):
    amount: MoneyStr
    status: str
    created_at: datetime


class OrderOut(BaseModel):
    reference: str
    status: OrderStatus
    status_label: str
    payment_status: PaymentStatus
    payment_status_label: str
    created_at: datetime
    paid_at: datetime | None
    payment_expires_at: datetime
    email: str
    customer_name: str
    phone: str
    shipping_address: OrderAddressOut
    billing_address: OrderAddressOut
    shipping_method: OrderShippingMethodOut
    coupon_code: str | None
    customer_note: str | None
    items: list[OrderItemOut]
    totals: OrderTotalsOut
    timeline: list[OrderEventOut]
    shipments: list[ShipmentOut]
    refunds: list[RefundOut]
    can_pay: bool
    can_cancel: bool
    payment_message: str | None


class OrderSummaryOut(BaseModel):
    reference: str
    status: OrderStatus
    status_label: str
    payment_status: PaymentStatus
    created_at: datetime
    grand_total: MoneyStr
    item_count: int
    first_item_name: str
    image: ImageOut | None


class CheckoutOrderOut(BaseModel):
    order: OrderOut
    access_token: str | None = Field(
        description="Guests only: private token for viewing this order (keep it secret)"
    )
    payment: PaymentSessionOut | None
    payment_error: str | None


class CancelOrderIn(StrictIn):
    reason: str | None = Field(default=None, max_length=300)


# --------------------------------------------------------------------------------------------
# Payments
# --------------------------------------------------------------------------------------------


class _PaymentRef(StrictIn):
    reference: str = Field(max_length=24)


class VerifyPaymentIn(_PaymentRef):
    provider_order_id: str = Field(max_length=64)
    provider_payment_id: str = Field(max_length=128)
    signature: str = Field(max_length=128)


class PaymentFailureIn(_PaymentRef):
    provider_order_id: str = Field(max_length=64)
    provider_payment_id: str | None = Field(default=None, max_length=128)


class RetryPaymentIn(_PaymentRef):
    pass


class SimulatorPayIn(_PaymentRef):
    provider_order_id: str = Field(max_length=64)
    outcome: Literal["success", "failure"]


class SimulatorPayOut(BaseModel):
    provider_order_id: str
    provider_payment_id: str
    signature: str | None
    status: str


class PaymentResultOut(BaseModel):
    outcome: Literal["paid", "processing", "failed", "review"]
    message: str
    order: OrderOut


class RetryPaymentOut(BaseModel):
    order: OrderOut
    payment: PaymentSessionOut
