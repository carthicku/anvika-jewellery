"""Inventory service — the ONLY module that writes inventory tables (ADR-0007).

Phase 3 provides reads and initial stock. Reservation/commit/release arrive with checkout (Phase 6).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InventoryLevel, InventoryMovement

StockStatus = Literal["in_stock", "low_stock", "out_of_stock"]


def levels_for(db: Session, variant_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, InventoryLevel]:
    ids = list(variant_ids)
    if not ids:
        return {}
    rows = db.scalars(select(InventoryLevel).where(InventoryLevel.variant_id.in_(ids))).all()
    return {row.variant_id: row for row in rows}


def stock_status(level: InventoryLevel | None) -> StockStatus:
    if level is None or level.available <= 0:
        return "out_of_stock"
    if level.available <= level.low_stock_threshold:
        return "low_stock"
    return "in_stock"


def set_initial_stock(
    db: Session,
    variant_id: uuid.UUID,
    quantity: int,
    *,
    low_stock_threshold: int = 2,
    actor_user_id: uuid.UUID | None = None,
    note: str = "Initial stock",
) -> InventoryLevel:
    """Create the stock row for a new variant and record the `initial` movement."""
    if quantity < 0:
        raise ValueError("Initial stock cannot be negative")
    level = InventoryLevel(
        variant_id=variant_id, on_hand=quantity, reserved=0, low_stock_threshold=low_stock_threshold
    )
    db.add(level)
    db.add(
        InventoryMovement(
            variant_id=variant_id,
            delta_on_hand=quantity,
            delta_reserved=0,
            reason="initial",
            actor_user_id=actor_user_id,
            note=note,
        )
    )
    return level
