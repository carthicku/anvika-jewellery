"""Orders, immutable line snapshots, timeline events, stock reservations, payments, refunds and
shipments. See docs/architecture/INVENTORY_AND_ORDERS.md and PAYMENT_FLOW.md."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey, enum_check

ORDER_STATUSES = (
    "pending_payment",
    "confirmed",
    "processing",
    "shipped",
    "delivered",
    "cancelled",
    "expired",
    "payment_review",
    "returned",
)
PAYMENT_STATUSES = (
    "unpaid",
    "authorized",
    "paid",
    "failed",
    "refund_pending",
    "partially_refunded",
    "refunded",
)
ACTOR_TYPES = ("customer", "admin", "system", "provider")
RESERVATION_STATUSES = ("active", "committed", "released")
PROVIDERS = ("razorpay", "simulator")
ATTEMPT_STATUSES = ("created", "authorized", "captured", "failed")
REFUND_STATUSES = ("requested", "pending", "processed", "failed")
SHIPMENT_STATUSES = ("pending", "shipped", "delivered", "returned")

_MONEY = Numeric(12, 2)


class Order(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(enum_check("status", ORDER_STATUSES), name="status"),
        CheckConstraint(enum_check("payment_status", PAYMENT_STATUSES), name="payment_status"),
        CheckConstraint("grand_total >= 0", name="grand_total_non_negative"),
        Index("ix_orders_user_created", "user_id", "created_at"),
        Index("ix_orders_status_created", "status", "created_at"),
        Index("ix_orders_payment_status", "payment_status"),
        Index(
            "ix_orders_pending_expiry",
            "payment_expires_at",
            postgresql_where=text("status = 'pending_payment'"),
        ),
    )

    reference: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    cart_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # Guests view their order through a private link; only the hash is stored.
    guest_access_token_hash: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_payment")
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unpaid")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    subtotal: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    automatic_discount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    coupon_discount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    taxable_total: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    tax_total: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    shipping_total: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    rounding_adjustment: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(40))

    shipping_address: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    billing_address: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    shipping_method: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Tax rates, engine version and display breakdown used for this order (audit trail).
    pricing_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    customer_note: Mapped[str | None] = mapped_column(String(500))

    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    terms_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payment_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", order_by="OrderItem.position", cascade="all, delete-orphan"
    )
    events: Mapped[list[OrderEvent]] = relationship(
        order_by="OrderEvent.created_at", cascade="all, delete-orphan"
    )


class OrderItem(UUIDPrimaryKey, Base):
    """Immutable snapshot of what was bought and how it was priced."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("ix_order_items_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL")
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    product_slug: Mapped[str] = mapped_column(String(180), nullable=False)
    variant_label: Mapped[str] = mapped_column(String(80), nullable=False)
    sku: Mapped[str] = mapped_column(String(40), nullable=False)
    purity: Mapped[str] = mapped_column(String(4), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    line_components: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    line_discount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    line_taxable_value: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    line_tax: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    # Engine inputs (rate, weights, making config, tax rates, discount) and return eligibility.
    price_inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")


class OrderEvent(UUIDPrimaryKey, Base):
    """Status timeline and audit trail of one order."""

    __tablename__ = "order_events"
    __table_args__ = (
        CheckConstraint(enum_check("actor_type", ACTOR_TYPES), name="actor_type"),
        Index("ix_order_events_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(String(500))
    customer_visible: Mapped[bool] = mapped_column(nullable=False, default=True)
    actor_type: Mapped[str] = mapped_column(String(10), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InventoryReservation(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        CheckConstraint(enum_check("status", RESERVATION_STATUSES), name="status"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("ix_inventory_reservations_order", "order_id"),
        Index("ix_inventory_reservations_status_expiry", "status", "expires_at"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaymentAttempt(UUIDPrimaryKey, Timestamps, Base):
    """One provider order (e.g. a Razorpay order) created to collect payment for an order."""

    __tablename__ = "payment_attempts"
    __table_args__ = (
        CheckConstraint(enum_check("provider", PROVIDERS), name="provider"),
        CheckConstraint(enum_check("status", ATTEMPT_STATUSES), name="status"),
        CheckConstraint("amount_paise > 0", name="amount_positive"),
        Index("ix_payment_attempts_order", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(10), nullable=False)
    provider_order_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="created")
    method: Mapped[str | None] = mapped_column(String(30))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_description: Mapped[str | None] = mapped_column(String(300))


class PaymentEvent(UUIDPrimaryKey, Base):
    """A signature-verified provider webhook, stored once per provider event id."""

    __tablename__ = "payment_events"

    provider: Mapped[str] = mapped_column(String(10), nullable=False)
    event_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_error: Mapped[str | None] = mapped_column(Text)


class Refund(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint(enum_check("status", REFUND_STATUSES), name="status"),
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_refunds_order", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    payment_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_attempts.id", ondelete="SET NULL")
    )
    provider_refund_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    amount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="requested")
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class Shipment(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint(enum_check("status", SHIPMENT_STATUSES), name="status"),
        Index("ix_shipments_order", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    carrier: Mapped[str] = mapped_column(String(80), nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(80), nullable=False)
    tracking_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="shipped")
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
