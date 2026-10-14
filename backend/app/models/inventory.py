"""Stock levels and the append-only movement ledger. See ADR-0007 and INVENTORY_AND_ORDERS.md.

Only app/services/inventory.py may write these tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey, enum_check
from app.models.enums import INVENTORY_REASONS


class InventoryLevel(Base):
    __tablename__ = "inventory_levels"
    __table_args__ = (
        CheckConstraint(
            "on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand", name="stock_consistent"
        ),
        CheckConstraint("low_stock_threshold >= 0", name="threshold_non_negative"),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True
    )
    on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


class InventoryMovement(UUIDPrimaryKey, Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(enum_check("reason", INVENTORY_REASONS), name="reason"),
        Index("ix_inventory_movements_variant_created", "variant_id", "created_at"),
        Index("ix_inventory_movements_order_id", "order_id"),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    delta_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delta_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(String(24), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
