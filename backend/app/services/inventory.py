"""Inventory service — the ONLY module that writes inventory tables (ADR-0007).

Reads, initial stock and the order lifecycle (docs/architecture/INVENTORY_AND_ORDERS.md §1):

| Operation | on_hand | reserved | Movement reason |
|-----------|:-:|:-:|-----------------|
| reserve   | –  | +q | reservation |
| release   | –  | −q | reservation_release |
| commit    | −q | −q | sale |
| restock   | +q | –  | cancellation_restock / return_restock |

Every write locks the `inventory_levels` rows with SELECT … FOR UPDATE in variant-id order (so two
checkouts can never deadlock or both take the last piece) and records a movement. The caller's
transaction commits everything together; the database CHECK constraint is the final guard.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import OutOfStock
from app.models import InventoryLevel, InventoryMovement, InventoryReservation

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


def stock_status_for(available: int, low_stock_threshold: int = 2) -> StockStatus:
    if available <= 0:
        return "out_of_stock"
    return "low_stock" if available <= low_stock_threshold else "in_stock"


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


# --------------------------------------------------------------------------------------------
# Order lifecycle (Phase 6)
# --------------------------------------------------------------------------------------------


def _lock_levels(db: Session, variant_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, InventoryLevel]:
    """Lock stock rows in a fixed (variant id) order so concurrent callers queue, not deadlock."""
    ids = sorted(set(variant_ids))
    if not ids:
        return {}
    rows = db.scalars(
        select(InventoryLevel)
        .where(InventoryLevel.variant_id.in_(ids))
        .order_by(InventoryLevel.variant_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    return {row.variant_id: row for row in rows}


def _movement(
    db: Session,
    variant_id: uuid.UUID,
    *,
    on_hand: int = 0,
    reserved: int = 0,
    reason: str,
    order_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    note: str | None = None,
) -> None:
    db.add(
        InventoryMovement(
            variant_id=variant_id,
            delta_on_hand=on_hand,
            delta_reserved=reserved,
            reason=reason,
            order_id=order_id,
            actor_user_id=actor_user_id,
            note=note,
        )
    )


def reserve(
    db: Session,
    order_id: uuid.UUID,
    lines: Iterable[tuple[uuid.UUID, int]],
    expires_at: datetime,
) -> list[InventoryReservation]:
    """Hold stock for a new (or late-paid) order. Raises OutOfStock listing every short line
    (`details.lines = [{variant_id, requested, available}]`) and changes nothing in that case."""
    wanted: dict[uuid.UUID, int] = defaultdict(int)
    for variant_id, quantity in lines:
        if quantity <= 0:
            raise ValueError("Reservation quantity must be positive")
        wanted[variant_id] += quantity
    levels = _lock_levels(db, wanted)
    short = []
    for variant_id, quantity in sorted(wanted.items()):
        level = levels.get(variant_id)
        available = level.available if level else 0
        if available < quantity:
            short.append(
                {
                    "variant_id": str(variant_id),
                    "requested": quantity,
                    "available": max(0, available),
                }
            )
    if short:
        raise OutOfStock(
            "Sorry, some pieces in your cart are no longer available in the quantity you chose.",
            details={"lines": short},
        )
    reservations = []
    for variant_id, quantity in sorted(wanted.items()):
        levels[variant_id].reserved += quantity
        reservation = InventoryReservation(
            order_id=order_id,
            variant_id=variant_id,
            quantity=quantity,
            status="active",
            expires_at=expires_at,
        )
        db.add(reservation)
        reservations.append(reservation)
        _movement(db, variant_id, reserved=quantity, reason="reservation", order_id=order_id)
    db.flush()
    return reservations


def _reservations(db: Session, order_id: uuid.UUID, status: str) -> list[InventoryReservation]:
    return list(
        db.scalars(
            select(InventoryReservation)
            .where(InventoryReservation.order_id == order_id, InventoryReservation.status == status)
            .order_by(InventoryReservation.variant_id)
            .with_for_update()
        ).all()
    )


def release(db: Session, order_id: uuid.UUID, note: str | None = None) -> int:
    """Give back the stock held by an unpaid order. Returns the number of pieces released.
    Safe to call twice: only `active` reservations are touched."""
    held = _reservations(db, order_id, "active")
    levels = _lock_levels(db, [r.variant_id for r in held])
    for r in held:
        levels[r.variant_id].reserved -= r.quantity
        r.status = "released"
        _movement(
            db,
            r.variant_id,
            reserved=-r.quantity,
            reason="reservation_release",
            order_id=order_id,
            note=note,
        )
    db.flush()
    return sum(r.quantity for r in held)


def commit(db: Session, order_id: uuid.UUID) -> int:
    """Turn an order's held stock into a sale (payment verified). Returns pieces committed."""
    held = _reservations(db, order_id, "active")
    levels = _lock_levels(db, [r.variant_id for r in held])
    for r in held:
        level = levels[r.variant_id]
        level.on_hand -= r.quantity
        level.reserved -= r.quantity
        r.status = "committed"
        _movement(
            db,
            r.variant_id,
            on_hand=-r.quantity,
            reserved=-r.quantity,
            reason="sale",
            order_id=order_id,
        )
    db.flush()
    return sum(r.quantity for r in held)


def restock(
    db: Session,
    order_id: uuid.UUID,
    lines: Iterable[tuple[uuid.UUID, int]],
    *,
    reason: str = "cancellation_restock",
    actor_user_id: uuid.UUID | None = None,
    note: str | None = None,
) -> None:
    """Put sold pieces back on the shelf (paid order cancelled, or an approved return received).
    The caller guarantees this runs once per order/return through the order state machine."""
    if reason not in ("cancellation_restock", "return_restock"):
        raise ValueError(f"Unsupported restock reason {reason!r}")
    quantities: dict[uuid.UUID, int] = defaultdict(int)
    for variant_id, quantity in lines:
        quantities[variant_id] += quantity
    levels = _lock_levels(db, quantities)
    for variant_id, quantity in sorted(quantities.items()):
        level = levels.get(variant_id)
        if level is None:  # variant deleted since the sale — nothing to put back
            continue
        level.on_hand += quantity
        _movement(
            db,
            variant_id,
            on_hand=quantity,
            reason=reason,
            order_id=order_id,
            actor_user_id=actor_user_id,
            note=note,
        )
    db.flush()
