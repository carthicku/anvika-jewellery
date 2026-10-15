"""Returns and exchanges (docs/architecture/INVENTORY_AND_ORDERS.md §5).

Flow: `requested → approved | rejected`, `approved → received | closed`,
`received → refunded | closed`. Customers ask for a return of delivered items that were
return/exchange eligible when they bought them, within the return window counted from delivery.
Staff decide; stock goes back on the shelf only for items they mark as resellable when the parcel
arrives (`return_restock`); money goes back only through the normal refund flow (a refund request
that an admin then sends to the payment provider).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.money import ZERO, format_inr, money
from app.core.time import utcnow
from app.models import Order, OrderEvent, OrderItem, Product, Refund, ReturnRequest, Shipment, User
from app.models.orders import OPEN_RETURN_STATUSES
from app.services import admin_orders, audit, inventory, orders

STATUS_LABELS = orders.RETURN_STATUS_LABELS
KIND_LABELS = orders.RETURN_KIND_LABELS

# What each admin action needs the request's status to be.
_ACTION_FROM = {
    "approve": ("requested",),
    "reject": ("requested",),
    "receive": ("approved",),
    "refund": ("received",),
    "close": ("approved", "received"),
}


@dataclass
class ReturnableItem:
    position: int
    product_name: str
    variant_label: str
    quantity: int  # how many can still be returned
    kinds: list[str]
    deadline: datetime


# --------------------------------------------------------------------------------------------
# Eligibility
# --------------------------------------------------------------------------------------------


def delivered_at(db: Session, order: Order) -> datetime | None:
    """When the order was delivered: the latest `delivered` timeline event, else the shipment."""
    event_time = db.scalar(
        select(func.max(OrderEvent.created_at)).where(
            OrderEvent.order_id == order.id, OrderEvent.kind == "delivered"
        )
    )
    if event_time is not None:
        return event_time
    return db.scalar(select(func.max(Shipment.delivered_at)).where(Shipment.order_id == order.id))


def _window_days(db: Session, item: OrderItem) -> int | None:
    """The return window snapshotted at purchase; older orders fall back to the product's
    current setting. `None` means the product has no online return window."""
    inputs = item.price_inputs or {}
    if "return_window_days" in inputs:
        value = inputs["return_window_days"]
        return int(value) if value is not None else None
    if item.product_id is None:
        return None
    current: int | None = db.scalar(
        select(Product.return_window_days).where(Product.id == item.product_id)
    )
    return current


def already_requested(db: Session, order: Order) -> dict[int, int]:
    """Quantity per item position already in a (non-rejected) return or exchange request."""
    taken: dict[int, int] = {}
    for request in db.scalars(
        select(ReturnRequest).where(
            ReturnRequest.order_id == order.id, ReturnRequest.status != "rejected"
        )
    ).all():
        for line in request.items:
            taken[int(line["position"])] = taken.get(int(line["position"]), 0) + int(
                line["quantity"]
            )
    return taken


def has_open_request(db: Session, order: Order) -> bool:
    return (
        db.scalar(
            select(ReturnRequest.id).where(
                ReturnRequest.order_id == order.id,
                ReturnRequest.status.in_(OPEN_RETURN_STATUSES),
            )
        )
        is not None
    )


def returnable_items(
    db: Session, order: Order, now: datetime | None = None
) -> list[ReturnableItem]:
    """Items the customer can ask to return or exchange right now (empty if none)."""
    if order.status != "delivered" or order.payment_status not in ("paid", "partially_refunded"):
        return []
    if has_open_request(db, order):
        return []
    delivered = delivered_at(db, order)
    if delivered is None:
        return []
    now = now or utcnow()
    taken = already_requested(db, order)
    result: list[ReturnableItem] = []
    for item in db.scalars(
        select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.position)
    ).all():
        inputs = item.price_inputs or {}
        kinds = [
            kind
            for kind, flag in (("return", "return_eligible"), ("exchange", "exchange_eligible"))
            if inputs.get(flag)
        ]
        days = _window_days(db, item)
        remaining = item.quantity - taken.get(item.position, 0)
        if not kinds or days is None or remaining <= 0:
            continue
        deadline = delivered + timedelta(days=days)
        if now > deadline:
            continue
        result.append(
            ReturnableItem(
                position=item.position,
                product_name=item.product_name,
                variant_label=item.variant_label,
                quantity=remaining,
                kinds=kinds,
                deadline=deadline,
            )
        )
    return result


# --------------------------------------------------------------------------------------------
# Customer request
# --------------------------------------------------------------------------------------------


def _status_email(db: Session, settings: Settings, order: Order, request: ReturnRequest) -> None:
    messages = {
        "requested": "We've received your request and will reply within two working days.",
        "approved": "Your request has been approved. Please send the items back as explained "
        "on your order page.",
        "rejected": "We're sorry, we can't accept this request.",
        "received": "The items you sent back have arrived and are being checked.",
        "refunded": "A refund has been issued for your returned items. You'll get a separate "
        "email when the payment provider has processed it.",
        "closed": "Your request is complete.",
    }
    message = messages[request.status]
    if request.store_note:
        message = f"{message} Note from us: {request.store_note}"
    orders.queue_email(
        db,
        settings,
        order,
        "return_update",
        "Update on your request for order {reference}",
        key_suffix=f":{request.id}:{request.status}",
        extra={"return_kind": KIND_LABELS[request.kind], "return_message": message},
    )


def create_request(
    db: Session,
    settings: Settings,
    order: Order,
    user: User | None,
    *,
    kind: str,
    reason: str,
    lines: list[tuple[int, int]],
) -> ReturnRequest:
    """Customer asks to return/exchange `lines` [(item position, quantity)]. The order must be
    locked by the caller (FOR UPDATE) so two requests can't race."""
    if order.status != "delivered":
        raise Conflict(
            "Returns can be requested once your order has been delivered.", code="NOT_DELIVERED"
        )
    if has_open_request(db, order):
        raise Conflict(
            "There is already an open request for this order. We'll update you on it soon.",
            code="RETURN_ALREADY_OPEN",
        )
    reason = reason.strip()
    if len(reason) < 10:
        raise ValidationFailed({"reason": "Please tell us a little more (at least 10 characters)."})
    eligible = {i.position: i for i in returnable_items(db, order)}
    if not eligible:
        raise Conflict(
            "Nothing in this order can be returned online any more. Please contact us.",
            code="RETURN_NOT_AVAILABLE",
        )
    wanted: dict[int, int] = {}
    for position, quantity in lines:
        wanted[position] = wanted.get(position, 0) + quantity
    if not wanted or any(q <= 0 for q in wanted.values()):
        raise ValidationFailed({"items": "Choose at least one item."})
    items = {
        i.position: i
        for i in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    }
    snapshot: list[dict[str, Any]] = []
    for position, quantity in sorted(wanted.items()):
        option = eligible.get(position)
        if option is None or kind not in option.kinds:
            raise ValidationFailed(
                {"items": f"Item {position} can't be included in a {kind} request."}
            )
        if quantity > option.quantity:
            raise ValidationFailed(
                {"items": f"At most {option.quantity} of item {position} can be returned."}
            )
        item = items[position]
        snapshot.append(
            {
                "position": position,
                "quantity": quantity,
                "product_name": item.product_name,
                "variant_label": item.variant_label,
                "sku": item.sku,
                "restock": None,
            }
        )
    request = ReturnRequest(
        order_id=order.id,
        user_id=user.id if user else None,
        kind=kind,
        status="requested",
        reason=reason[:500],
        items=snapshot,
    )
    db.add(request)
    db.flush()
    orders.add_event(
        db,
        order,
        "return_requested",
        actor_type="customer",
        actor_user_id=user.id if user else None,
        note=KIND_LABELS[kind],
    )
    _status_email(db, settings, order, request)
    return request


# --------------------------------------------------------------------------------------------
# Staff decisions
# --------------------------------------------------------------------------------------------


def find(db: Session, request_id: uuid.UUID, *, lock: bool = False) -> ReturnRequest:
    stmt = select(ReturnRequest).where(ReturnRequest.id == request_id)
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    request = db.scalar(stmt)
    if request is None:
        raise NotFound("Return request not found.")
    return request


def filtered(status: str | None) -> Select[ReturnRequest]:
    stmt = select(ReturnRequest)
    if status:
        stmt = stmt.where(ReturnRequest.status == status)
    return stmt


def allowed_actions(request: ReturnRequest) -> list[str]:
    actions = [a for a, states in _ACTION_FROM.items() if request.status in states]
    if request.kind == "exchange" and "refund" in actions:
        actions.remove("refund")
    return actions


def suggested_refund(db: Session, request: ReturnRequest, order: Order) -> Decimal:
    """The returned lines' share of what was paid for them (shipping is not included), capped
    at what is still refundable. Staff can change the amount."""
    if request.kind != "return":
        return ZERO
    items = {
        i.position: i
        for i in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    }
    total = ZERO
    for line in request.items:
        item = items.get(int(line["position"]))
        if item is not None:
            total += item.line_total * Decimal(int(line["quantity"])) / Decimal(item.quantity)
    return min(money(total), orders.refundable_amount(db, order))


def _check(request: ReturnRequest, action: str) -> None:
    if request.status not in _ACTION_FROM[action] or action not in allowed_actions(request):
        raise Conflict(
            f"A request that is {STATUS_LABELS[request.status].lower()} can't be changed that way.",
            code="INVALID_RETURN_STATE",
        )


def _record(
    db: Session,
    settings: Settings,
    actor: User,
    order: Order,
    request: ReturnRequest,
    action: str,
    note: str | None,
    ip: str | None,
    changes: dict[str, object] | None = None,
) -> None:
    request.updated_at = utcnow()
    if note:
        request.store_note = note.strip()[:500]
    orders.add_event(
        db,
        order,
        f"return_{request.status}",
        actor_type="admin",
        actor_user_id=actor.id,
        note=note.strip()[:500] if note else None,
    )
    audit.record(
        db,
        actor=actor,
        action=f"return.{action}",
        entity_type="return_request",
        entity_id=str(request.id),
        changes={"order": order.reference, "status": request.status, **(changes or {})},
        ip_address=ip,
    )
    _status_email(db, settings, order, request)
    db.flush()


def decide(
    db: Session,
    settings: Settings,
    actor: User,
    request: ReturnRequest,
    order: Order,
    *,
    approve: bool,
    note: str,
    ip: str | None = None,
) -> None:
    action = "approve" if approve else "reject"
    _check(request, action)
    if not approve and len(note.strip()) < 3:
        raise ValidationFailed({"note": "Tell the customer why the request can't be accepted."})
    request.status = "approved" if approve else "rejected"
    request.decided_by = actor.id
    request.decided_at = utcnow()
    _record(db, settings, actor, order, request, action, note, ip)


def receive(
    db: Session,
    settings: Settings,
    actor: User,
    request: ReturnRequest,
    order: Order,
    *,
    restock_positions: set[int],
    note: str,
    ip: str | None = None,
) -> None:
    """The parcel arrived. Resellable items go back into stock (`return_restock`); once every
    piece of the order has come back for a refund, the order becomes `returned`."""
    _check(request, "receive")
    positions = {int(line["position"]) for line in request.items}
    unknown = restock_positions - positions
    if unknown:
        raise ValidationFailed({"restock": "Only items in this request can be restocked."})
    items = {
        i.position: i
        for i in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    }
    restock_lines: list[tuple[uuid.UUID, int]] = []
    updated: list[dict[str, Any]] = []
    for line in request.items:
        position = int(line["position"])
        restock = position in restock_positions
        updated.append({**line, "restock": restock})
        variant_id = items[position].variant_id if position in items else None
        if restock and variant_id is not None:
            restock_lines.append((variant_id, int(line["quantity"])))
    request.items = updated  # reassign so the JSONB change is saved
    if restock_lines:
        inventory.restock(
            db,
            order.id,
            restock_lines,
            reason="return_restock",
            actor_user_id=actor.id,
            note=f"Return {str(request.id)[:8]} for {order.reference}",
        )
    request.status = "received"
    request.received_at = utcnow()
    _record(
        db,
        settings,
        actor,
        order,
        request,
        "receive",
        note,
        ip,
        {"restocked": sorted(restock_positions)},
    )
    if request.kind == "return" and _fully_returned(db, order):
        orders.transition(
            db,
            order,
            "returned",
            kind="order_returned",
            actor_type="admin",
            actor_user_id=actor.id,
        )


def _fully_returned(db: Session, order: Order) -> bool:
    returned: dict[int, int] = {}
    for request in db.scalars(
        select(ReturnRequest).where(
            ReturnRequest.order_id == order.id,
            ReturnRequest.kind == "return",
            ReturnRequest.status.in_(("received", "refunded")),
        )
    ).all():
        for line in request.items:
            position = int(line["position"])
            returned[position] = returned.get(position, 0) + int(line["quantity"])
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    return all(returned.get(i.position, 0) >= i.quantity for i in items)


def refund(
    db: Session,
    settings: Settings,
    actor: User,
    request: ReturnRequest,
    order: Order,
    *,
    amount: Decimal,
    note: str,
    ip: str | None = None,
) -> Refund:
    """Create the refund request for a received return. Sending it to the payment provider is
    the usual order refund action (`orders:refund`)."""
    _check(request, "refund")
    if order.paid_at is None:
        raise Conflict("This order has no payment to refund.", code="NOT_PAID")
    refund_row = admin_orders.request_refund(
        db, actor, order, amount, f"Return {str(request.id)[:8]}: {request.reason}"[:300]
    )
    request.refund_id = refund_row.id
    request.status = "refunded"
    _record(
        db,
        settings,
        actor,
        order,
        request,
        "refund",
        note,
        ip,
        {"refund_id": str(refund_row.id), "amount": str(refund_row.amount)},
    )
    return refund_row


def close(
    db: Session,
    settings: Settings,
    actor: User,
    request: ReturnRequest,
    order: Order,
    *,
    note: str,
    ip: str | None = None,
) -> None:
    """Finish without a refund: an exchange was sent out, or the customer never sent the items."""
    _check(request, "close")
    if len(note.strip()) < 3:
        raise ValidationFailed({"note": "Say how this request was completed."})
    request.status = "closed"
    _record(db, settings, actor, order, request, "close", note, ip)


def refund_label(db: Session, request: ReturnRequest) -> str | None:
    if request.refund_id is None:
        return None
    row = db.get(Refund, request.refund_id)
    return f"{format_inr(row.amount)} · {row.status}" if row else None
