"""Carts, cart lines, coupons and coupon redemptions. See docs/architecture/PRICING_ENGINE.md §6."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey, enum_check

CART_STATUSES = ("active", "converted", "merged", "abandoned")
COUPON_KINDS = ("percent", "flat")
REDEMPTION_STATUSES = ("reserved", "redeemed", "released")
MAX_LINE_QUANTITY = 10


class Cart(UUIDPrimaryKey, Timestamps, Base):
    """A guest cart (identified by a hashed cookie token) or a customer's cart."""

    __tablename__ = "carts"
    __table_args__ = (
        CheckConstraint(enum_check("status", CART_STATUSES), name="status"),
        CheckConstraint("user_id IS NOT NULL OR token_hash IS NOT NULL", name="has_owner"),
        Index(
            "uq_carts_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active' AND user_id IS NOT NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    coupon_code: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    items: Mapped[list[CartItem]] = relationship(
        back_populates="cart", order_by="CartItem.created_at", cascade="all, delete-orphan"
    )


class CartItem(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id"),
        CheckConstraint(f"quantity BETWEEN 1 AND {MAX_LINE_QUANTITY}", name="quantity_range"),
    )

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # The unit price (incl. tax) the customer last saw and accepted. A higher current price blocks
    # checkout until the customer accepts it again (PRICING_ENGINE.md §6).
    accepted_unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    cart: Mapped[Cart] = relationship(back_populates="items")


class Coupon(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint(enum_check("kind", COUPON_KINDS), name="kind"),
        CheckConstraint("code = upper(code)", name="code_uppercase"),
        CheckConstraint("value > 0", name="value_positive"),
        CheckConstraint("kind = 'flat' OR value <= 100", name="percent_at_most_100"),
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="window_valid"),
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_limit_total: Mapped[int | None] = mapped_column(Integer)
    usage_limit_per_customer: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CouponRedemption(UUIDPrimaryKey, Base):
    """One per order that used a coupon; `reserved` and `redeemed` count towards usage limits."""

    __tablename__ = "coupon_redemptions"
    __table_args__ = (
        CheckConstraint(enum_check("status", REDEMPTION_STATUSES), name="status"),
        Index("ix_coupon_redemptions_coupon_status", "coupon_id", "status"),
    )

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coupons.id", ondelete="RESTRICT"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="reserved")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
