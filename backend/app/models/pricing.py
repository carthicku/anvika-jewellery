"""Pricing data: gold rate history and automatic discounts (see PRICING_ENGINE.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UUIDPrimaryKey, enum_check
from app.models.enums import DISCOUNT_KINDS, DISCOUNT_SCOPES, PURITIES


class GoldRate(UUIDPrimaryKey, Base):
    """Append-only. The current rate for a purity is the latest row with effective_from <= now."""

    __tablename__ = "gold_rates"
    __table_args__ = (
        CheckConstraint(enum_check("purity", PURITIES), name="purity"),
        CheckConstraint("rate_per_gram > 0", name="rate_positive"),
        Index("ix_gold_rates_purity_effective", "purity", "effective_from"),
    )

    purity: Mapped[str] = mapped_column(String(4), nullable=False)
    rate_per_gram: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_note: Mapped[str] = mapped_column(String(300), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Discount(UUIDPrimaryKey, Timestamps, Base):
    """Automatic promotion. At most one (the best for the customer) applies per cart line."""

    __tablename__ = "discounts"
    __table_args__ = (
        CheckConstraint(enum_check("kind", DISCOUNT_KINDS), name="kind"),
        CheckConstraint(enum_check("scope", DISCOUNT_SCOPES), name="scope"),
        CheckConstraint("value > 0", name="value_positive"),
        CheckConstraint("kind = 'flat_off_price' OR value <= 100", name="percent_at_most_100"),
        CheckConstraint("(scope = 'all') = (scope_id IS NULL)", name="scope_id_matches_scope"),
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="window_valid"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="all")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
