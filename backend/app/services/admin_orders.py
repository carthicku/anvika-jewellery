"""Order management for staff (INVENTORY_AND_ORDERS.md §2, PAYMENT_FLOW.md §2.10–11).

Every action goes through the order state machine (`orders.transition`), writes an internal
timeline event and an audit-log entry. Staff can never set `payment_status` directly: it changes
only through verified payments and refunds.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import Conflict, NotFound, OutOfStock, ValidationFailed
from app.core.money import ZERO, format_inr, money, to_paise
from app.core.time import utcnow
from app.models import Order, OrderEvent, OrderItem, PaymentAttempt, Refund, Shipment, User
from app.services import audit, inventory, orders
from app.services.payment_gateway import PaymentGateway
from app.services.payments import apply_refund_status


def find(db: Session, reference: str, *, lock: bool = False) -> Order:
    stmt = select(Order).where(Order.reference == reference.strip().upper())
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    order = db.scalar(stmt)
    if order is None:
        raise NotFound("Order not found.")
    return order


@dataclass
class OrderFilters:
    status: str | None = None
    payment_status: str | None = None
    q: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


def filtered(f: OrderFilters) -> Select[Order]:
    stmt = select(Order)
    if f.status:
        stmt = stmt.where(Order.status == f.status)
    if f.payment_status:
        stmt = stmt.where(Order.payment_status == f.payment_status)
    if f.q:
        like = f"%{f.q.strip().replace('%', '').replace('_', '')}%"
        stmt = stmt.where(
            or_(
                Order.reference.ilike(like),
                Order.email.ilike(like),
                Order.customer_name.ilike(like),
                Order.phone.ilike(like),
            )
        )
    if f.date_from:
        stmt = stmt.where(Order.created_at >= f.date_from)
    if f.date_to:
        stmt = stmt.where(Order.created_at < f.date_to)
    return stmt


def list_orders(db: Session, f: OrderFilters, page: int, page_size: int) -> tuple[list[Order], int]:
    stmt = filtered(f)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Order.created_at.desc(), Order.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def allowed_actions(db: Session, order: Order) -> list[str]:
    actions: list[str] = []
    paid = order.payment_status == "paid"
    if order.status == "confirmed" and paid:
        actions.append("start_processing")
    if order.status == "processing" and paid:
        actions.append("ship")
    if order.status == "shipped":
        actions.append("mark_delivered")
    if order.status in ("pending_payment", "confirmed", "processing") and order.payment_status != (
        "authorized"
    ):
        actions.append("cancel")
    if order.status == "payment_review":
        actions += ["resolve_confirm", "resolve_refund"]
    if order.paid_at is not None and orders.refundable_amount(db, order) > ZERO:
        actions.append("refund")
    if db.scalar(
        select(Refund.id).where(Refund.order_id == order.id, Refund.status == "requested")
    ):
        actions.append("execute_refund")
    actions.append("note")
    return actions


# --------------------------------------------------------------------------------------------
# Fulfilment
# --------------------------------------------------------------------------------------------


def _audit(
    db: Session, actor: User, order: Order, action: str, changes: dict[str, object], ip: str | None
) -> None:
    audit.record(
        db,
        actor=actor,
        action=f"order.{action}",
        entity_type="order",
        entity_id=order.reference,
        changes=changes,
        ip_address=ip,
    )


def start_processing(db: Session, actor: User, order: Order, ip: str | None = None) -> None:
    if order.payment_status != "paid":
        raise Conflict("Only paid orders can be prepared.", code="NOT_PAID")
    orders.transition(
        db, order, "processing", kind="status_changed", actor_type="admin", actor_user_id=actor.id
    )
    _audit(db, actor, order, "processing", {"status": "processing"}, ip)


def ship(
    db: Session,
    settings: Settings,
    actor: User,
    order: Order,
    *,
    carrier: str,
    tracking_number: str,
    tracking_url: str | None,
    ip: str | None = None,
) -> Shipment:
    if order.payment_status != "paid":
        raise Conflict("Only paid orders can be shipped.", code="NOT_PAID")
    now = utcnow()
    shipment = Shipment(
        order_id=order.id,
        carrier=carrier.strip(),
        tracking_number=tracking_number.strip(),
        tracking_url=tracking_url,
        status="shipped",
        shipped_at=now,
    )
    db.add(shipment)
    orders.transition(
        db,
        order,
        "shipped",
        kind="shipped",
        actor_type="admin",
        actor_user_id=actor.id,
        note=f"{shipment.carrier} · {shipment.tracking_number}",
    )
    _audit(db, actor, order, "shipped", {"carrier": carrier, "tracking": tracking_number}, ip)
    orders.queue_email(db, settings, order, "order_shipped", "Your order {reference} is on its way")
    db.flush()
    return shipment


def mark_delivered(db: Session, actor: User, order: Order, ip: str | None = None) -> None:
    orders.transition(
        db, order, "delivered", kind="delivered", actor_type="admin", actor_user_id=actor.id
    )
    now = utcnow()
    for shipment in db.scalars(select(Shipment).where(Shipment.order_id == order.id)).all():
        if shipment.status == "shipped":
            shipment.status = "delivered"
            shipment.delivered_at = now
    _audit(db, actor, order, "delivered", {"status": "delivered"}, ip)


def cancel(
    db: Session, settings: Settings, actor: User, order: Order, reason: str, ip: str | None = None
) -> None:
    if not reason.strip():
        raise ValidationFailed({"reason": "A reason is required."})
    if order.status not in ("pending_payment", "confirmed", "processing"):
        raise Conflict("This order can't be cancelled.", code="CANNOT_CANCEL")
    orders.cancel_order(
        db, settings, order, actor_type="admin", actor_user_id=actor.id, reason=reason.strip()
    )
    _audit(db, actor, order, "cancelled", {"reason": reason.strip()}, ip)


def add_note(db: Session, actor: User, order: Order, note: str, ip: str | None = None) -> None:
    if not note.strip():
        raise ValidationFailed({"note": "Write a note."})
    orders.add_event(
        db,
        order,
        "note",
        actor_type="admin",
        actor_user_id=actor.id,
        note=note.strip()[:500],
        customer_visible=False,
    )
    _audit(db, actor, order, "note", {"note": note.strip()[:500]}, ip)


def resolve_review(
    db: Session,
    settings: Settings,
    actor: User,
    order: Order,
    decision: str,
    note: str,
    ip: str | None = None,
) -> None:
    """A paid order that couldn't be confirmed automatically: fulfil it (if stock allows) or
    cancel it with a full refund request."""
    if order.status != "payment_review":
        raise Conflict("This order isn't waiting for review.", code="NOT_IN_REVIEW")
    if decision == "confirm":
        items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
        lines = [(i.variant_id, i.quantity) for i in items if i.variant_id is not None]
        if len(lines) != len(items):
            raise OutOfStock("A product in this order no longer exists; refund it instead.")
        inventory.reserve(db, order.id, lines, utcnow())
        inventory.commit(db, order.id)
        orders.set_redemption_status(db, order, "redeemed")
        orders.transition(
            db,
            order,
            "confirmed",
            kind="order_confirmed",
            actor_type="admin",
            actor_user_id=actor.id,
        )
        orders.queue_email(
            db, settings, order, "order_confirmation", "Your order {reference} is confirmed"
        )
    elif decision == "refund":
        orders.transition(
            db,
            order,
            "cancelled",
            kind="order_cancelled",
            actor_type="admin",
            actor_user_id=actor.id,
            note="We couldn't fulfil this order. A full refund has been requested.",
        )
        order.cancelled_at = utcnow()
        if order.payment_status == "paid":
            request_refund(db, actor, order, orders.refundable_amount(db, order), note or "Review")
        orders.queue_email(
            db, settings, order, "order_cancelled", "Your order {reference} has been cancelled"
        )
    else:
        raise ValidationFailed({"decision": "Choose confirm or refund."})
    _audit(db, actor, order, f"review_{decision}", {"note": note}, ip)


# --------------------------------------------------------------------------------------------
# Refunds
# --------------------------------------------------------------------------------------------


def request_refund(db: Session, actor: User, order: Order, amount: Decimal, reason: str) -> Refund:
    amount = money(amount)
    if amount <= ZERO:
        raise ValidationFailed({"amount": "Enter an amount above zero."})
    if amount > orders.refundable_amount(db, order):
        limit = format_inr(orders.refundable_amount(db, order))
        raise ValidationFailed({"amount": f"At most {limit} can be refunded."})
    refund = Refund(
        order_id=order.id, amount=amount, status="requested", reason=reason, requested_by=actor.id
    )
    db.add(refund)
    order.payment_status = "refund_pending"
    orders.add_event(db, order, "refund_requested", actor_type="admin", actor_user_id=actor.id)
    db.flush()
    return refund


def _captured_attempt(db: Session, order: Order) -> PaymentAttempt:
    attempt = db.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.order_id == order.id, PaymentAttempt.status == "captured")
        .order_by(PaymentAttempt.updated_at.desc())
        .limit(1)
    )
    if attempt is None or attempt.provider_payment_id is None:
        raise Conflict("No captured payment was found for this order.", code="NO_CAPTURED_PAYMENT")
    return attempt


def execute_refund(
    db: Session,
    settings: Settings,
    gateway: PaymentGateway,
    actor: User,
    order: Order,
    refund_id: uuid.UUID,
    ip: str | None = None,
) -> Refund:
    """Send a requested refund to the payment provider. The record moves to `pending` (or
    `processed` if the provider says so immediately); `refund.processed` webhooks finish it."""
    refund = db.scalar(
        select(Refund).where(Refund.id == refund_id, Refund.order_id == order.id).with_for_update()
    )
    if refund is None:
        raise NotFound("Refund not found.")
    if refund.status != "requested":
        raise Conflict("This refund has already been sent.", code="REFUND_ALREADY_SENT")
    attempt = (
        db.get(PaymentAttempt, refund.payment_attempt_id)
        if refund.payment_attempt_id
        else _captured_attempt(db, order)
    )
    if attempt is None or attempt.provider_payment_id is None:
        raise Conflict("No captured payment was found for this order.", code="NO_CAPTURED_PAYMENT")
    if attempt.provider != gateway.name:
        raise Conflict(
            f"This payment was taken with {attempt.provider}; switch the store to that provider "
            "to refund it.",
            code="PROVIDER_MISMATCH",
        )
    result = gateway.refund(
        attempt.provider_payment_id,
        to_paise(refund.amount),
        {"order_reference": order.reference, "refund_id": str(refund.id)},
    )
    refund.provider_refund_id = result.id
    refund.payment_attempt_id = attempt.id
    refund.status = "pending"
    if result.status == "processed":
        apply_refund_status(db, refund, "processed", settings)
    _audit(
        db,
        actor,
        order,
        "refund_sent",
        {"refund_id": str(refund.id), "amount": str(refund.amount), "status": refund.status},
        ip,
    )
    db.flush()
    return refund


def events(db: Session, order: Order) -> list[OrderEvent]:
    return list(
        db.scalars(
            select(OrderEvent)
            .where(OrderEvent.order_id == order.id)
            .order_by(OrderEvent.created_at, OrderEvent.id)
        ).all()
    )
