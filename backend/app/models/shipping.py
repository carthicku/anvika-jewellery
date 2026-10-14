"""Shipping methods and optional serviceable PIN-code zones (see SHIPPING_SETUP.md)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UUIDPrimaryKey


class ShippingMethod(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "shipping_methods"
    __table_args__ = (
        CheckConstraint("fee >= 0", name="fee_non_negative"),
        CheckConstraint("free_above IS NULL OR free_above >= 0", name="free_above_non_negative"),
        CheckConstraint("min_days >= 0 AND max_days >= min_days", name="days_range"),
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal(0))
    free_above: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    min_days: Mapped[int] = mapped_column(Integer, nullable=False)
    max_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ShippingZone(UUIDPrimaryKey, Timestamps, Base):
    """If any active zone exists, only PIN codes matching one of its prefixes are serviceable."""

    __tablename__ = "shipping_zones"
    __table_args__ = (CheckConstraint("extra_days >= 0", name="extra_days_non_negative"),)

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    pincode_prefixes: Mapped[list[str]] = mapped_column(ARRAY(String(6)), nullable=False)
    extra_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
