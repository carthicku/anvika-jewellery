"""Orders: status machine, timeline events, access control, customer views and cancellation.
See docs/architecture/INVENTORY_AND_ORDERS.md §2 and §4.

`payment_status` is changed only by app/services/payments.py (and the refund flow), never by
an ordinary status change.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.errors import Conflict, InvalidStateTransition, NotFound
from app.core.money import ZERO, format_inr
from app.core.security import hash_token
from app.core.time import utcnow
from app.models import (
    CouponRedemption,
    Order,
    OrderEvent,
    OrderItem,
    Refund,
    ReturnRequest,
    Shipment,
    User,
)
from app.schemas.catalogue import ImageOut, PriceRowOut
from app.schemas.common import Page
from app.schemas.orders import (
    OrderAddressOut,
    OrderEventOut,
    OrderItemOut,
    OrderOut,
    OrderShippingMethodOut,
    OrderSummaryOut,
    OrderTotalsOut,
    RefundOut,
    ReturnableItemOut,
    ReturnLineOut,
    ReturnOut,
    ShipmentOut,
)
from app.services import email as email_service
from app.services import inventory
from app.services.shipping import IST

STATUS_LABELS = {
    "pending_payment": "Awaiting payment",
    "confirmed": "Confirmed",
    "processing": "Being prepared",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
    "expired": "Payment not completed",
    "payment_review": "Payment being reviewed",
    "returned": "Returned",
}
PAYMENT_LABELS = {
    "unpaid": "Not paid",
    "authorized": "Payment being confirmed",
    "paid": "Paid",
    "failed": "Payment failed",
    "refund_pending": "Refund in progress",
    "partially_refunded": "Partly refunded",
    "refunded": "Refunded",
}
# Customer-facing titles for timeline events.
EVENT_TITLES = {
    "order_created": "Order placed — awaiting payment",
    "payment_failed": "Payment didn't go through",
    "payment_authorized": "Payment received — confirming with the bank",
    "payment_captured": "Payment received",
    "order_confirmed": "Order confirmed",
    "order_expired": "Payment window closed",
    "order_cancelled": "Order cancelled",
    "refund_requested": "Refund requested",
    "refund_processed": "Refund processed",
    "payment_review": "Payment received — we're reviewing your order",
    "status_changed": "Status updated",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "order_returned": "Order returned",
    "return_requested": "Return or exchange requested",
    "return_approved": "Return approved",
    "return_rejected": "Return not accepted",
    "return_received": "Returned items received",
    "return_refunded": "Refund issued for returned items",
    "return_closed": "Return or exchange completed",
}

RETURN_STATUS_LABELS = {
    "requested": "Requested — waiting for our reply",
    "approved": "Approved — please send the items back",
    "rejected": "Not accepted",
    "received": "Items received",
    "refunded": "Refund issued",
    "closed": "Completed",
}
RETURN_KIND_LABELS = {"return": "Return for a refund", "exchange": "Exchange"}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"confirmed", "expired", "cancelled", "payment_review"},
    "expired": {"confirmed", "payment_review"},
    "cancelled": {"payment_review"},
    "payment_review": {"confirmed", "cancelled"},
    "confirmed": {"processing", "cancelled"},
    "processing": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": {"returned"},
    "returned": set(),
}

# Unambiguous characters for human-readable references (no 0/O, 1/I/L).
_REFERENCE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


# --------------------------------------------------------------------------------------------
# References and guest access
# --------------------------------------------------------------------------------------------


def new_reference(db: Session, settings: Settings) -> str:
    today = utcnow().astimezone(IST).strftime("%y%m%d")
    while True:
        suffix = "".join(secrets.choice(_REFERENCE_ALPHABET) for _ in range(6))
        reference = f"{settings.order_reference_prefix}-{today}-{suffix}"
        if db.scalar(select(Order.id).where(Order.reference == reference)) is None:
            return reference


def guest_access_token(settings: Settings, order_id: uuid.UUID) -> str:
    """Private token for a guest's order link. Derived with the server secret so a repeated
    (idempotent) checkout request can return it again; only its hash is stored."""
    digest = hmac.new(
        settings.secret_key.get_secret_value().encode(),
        f"order-access:{order_id}".encode(),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def find_order(
    db: Session,
    reference: str,
    user: User | None,
    access_token: str | None,
    *,
    lock: bool = False,
) -> Order:
    """The order if this visitor may see it; otherwise 404 (never reveal that it exists)."""
    stmt = select(Order).where(Order.reference == reference.strip().upper())
    if lock:
        stmt = stmt.with_for_update()
    order = db.scalar(stmt)
    if order is None:
        raise NotFound("We couldn't find that order.")
    if user is not None and order.user_id == user.id:
        return order
    if (
        access_token
        and order.guest_access_token_hash
        and hmac.compare_digest(hash_token(access_token), order.guest_access_token_hash)
    ):
        return order
    raise NotFound("We couldn't find that order.")


def lock_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None:
        raise NotFound("We couldn't find that order.")
    return order


# --------------------------------------------------------------------------------------------
# Status machine and events
# --------------------------------------------------------------------------------------------


def add_event(
    db: Session,
    order: Order,
    kind: str,
    *,
    actor_type: str,
    actor_user_id: uuid.UUID | None = None,
    note: str | None = None,
    customer_visible: bool = True,
    from_status: str | None = None,
    to_status: str | None = None,
) -> None:
    db.add(
        OrderEvent(
            order_id=order.id,
            kind=kind,
            from_status=from_status,
            to_status=to_status,
            note=note,
            customer_visible=customer_visible,
            actor_type=actor_type,
            actor_user_id=actor_user_id,
            created_at=utcnow(),
        )
    )


def transition(
    db: Session,
    order: Order,
    to_status: str,
    *,
    kind: str,
    actor_type: str,
    actor_user_id: uuid.UUID | None = None,
    note: str | None = None,
    customer_visible: bool = True,
) -> None:
    """The only way an order's status changes. Anything not in ALLOWED_TRANSITIONS is refused."""
    if to_status not in ALLOWED_TRANSITIONS.get(order.status, set()):
        raise InvalidStateTransition(
            f"An order that is {STATUS_LABELS[order.status].lower()} can't be "
            f"changed to {STATUS_LABELS[to_status].lower()}.",
            details={"from": order.status, "to": to_status},
        )
    previous = order.status
    order.status = to_status
    order.updated_at = utcnow()
    add_event(
        db,
        order,
        kind,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        note=note,
        customer_visible=customer_visible,
        from_status=previous,
        to_status=to_status,
    )


# --------------------------------------------------------------------------------------------
# Coupons attached to orders
# --------------------------------------------------------------------------------------------


def set_redemption_status(db: Session, order: Order, status: str) -> None:
    redemption = db.scalar(select(CouponRedemption).where(CouponRedemption.order_id == order.id))
    if redemption is not None:
        redemption.status = status


# --------------------------------------------------------------------------------------------
# Emails
# --------------------------------------------------------------------------------------------


def order_link(settings: Settings, order: Order) -> str:
    base = settings.public_site_url.rstrip("/")
    if order.user_id is not None:
        return f"{base}/account/orders/{order.reference}"
    token = guest_access_token(settings, order.id)
    return f"{base}/order-confirmation/{order.reference}#token={token}"


def queue_email(
    db: Session,
    settings: Settings,
    order: Order,
    template: str,
    subject: str,
    *,
    key_suffix: str = "",
    extra: dict[str, str] | None = None,
) -> None:
    """Queue a customer email once per order/template (+ suffix, e.g. one per refund)."""
    items = db.scalars(
        select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.position)
    ).all()
    summary = "; ".join(f"{i.product_name} ({i.variant_label}) × {i.quantity}" for i in items)
    email_service.enqueue(
        db,
        key=f"order:{order.id}:{template}{key_suffix}",
        to=order.email,
        template=template,
        subject=subject.format(reference=order.reference),
        context={
            "name": order.customer_name,
            "reference": order.reference,
            "items": summary,
            "total": format_inr(order.grand_total),
            "order_url": order_link(settings, order),
            **(extra or {}),
        },
    )


# --------------------------------------------------------------------------------------------
# Cancellation (customer; admin cancellation reuses this in Phase 7)
# --------------------------------------------------------------------------------------------


def can_customer_cancel(order: Order) -> bool:
    if order.status == "pending_payment":
        return order.payment_status in ("unpaid", "failed")
    return order.status == "confirmed" and order.payment_status == "paid"


def cancel_order(
    db: Session,
    settings: Settings,
    order: Order,
    *,
    actor_type: str,
    actor_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> None:
    """Cancel an order (caller holds the row lock and commits).

    * Unpaid → stock released, coupon released.
    * Paid and not yet being prepared → stock put back and a full refund **requested** (an admin
      executes it with the payment provider; we never claim money was returned before it was).
    """
    if order.status == "pending_payment" and order.payment_status == "authorized":
        raise Conflict(
            "A payment for this order is still being confirmed, so it can't be cancelled yet. "
            "Please try again in a few minutes.",
            code="PAYMENT_IN_PROGRESS",
        )
    was_paid = order.payment_status == "paid"
    note = reason or ("Cancelled at the customer's request" if actor_type == "customer" else None)
    transition(
        db,
        order,
        "cancelled",
        kind="order_cancelled",
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        note=note,
    )
    order.cancelled_at = utcnow()
    if was_paid:
        items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
        inventory.restock(
            db,
            order.id,
            [(i.variant_id, i.quantity) for i in items if i.variant_id is not None],
            reason="cancellation_restock",
            actor_user_id=actor_user_id,
            note=f"Order {order.reference} cancelled",
        )
        db.add(
            Refund(
                order_id=order.id,
                amount=order.grand_total,
                status="requested",
                reason=note or "Order cancelled",
                requested_by=actor_user_id,
            )
        )
        order.payment_status = "refund_pending"
        add_event(
            db, order, "refund_requested", actor_type="system", note=format_inr(order.grand_total)
        )
        set_redemption_status(db, order, "released")
    else:
        inventory.release(db, order.id, note=f"Order {order.reference} cancelled")
        set_redemption_status(db, order, "released")
    queue_email(db, settings, order, "order_cancelled", "Your order {reference} has been cancelled")


# --------------------------------------------------------------------------------------------
# Views
# --------------------------------------------------------------------------------------------


def _address(data: dict[str, Any]) -> OrderAddressOut:
    return OrderAddressOut(**{k: data.get(k) for k in OrderAddressOut.model_fields if k in data})


def _image(item: OrderItem) -> ImageOut | None:
    return ImageOut(url=item.image_url, alt=item.product_name) if item.image_url else None


def _payment_message(order: Order) -> str | None:
    if order.status == "pending_payment":
        if order.payment_status == "authorized":
            return "We've received your payment and are waiting for the bank to confirm it."
        if order.payment_status == "failed":
            return "Your last payment attempt didn't go through. You can try again."
        return "Your pieces are reserved until the payment window closes."
    if order.status == "expired":
        return "The payment window closed before payment was completed. Nothing was charged."
    if order.status == "payment_review":
        return (
            "We received your payment but need to review this order. We'll contact you shortly; "
            "if we can't fulfil it, the full amount will be refunded."
        )
    return None


def can_pay(order: Order, now: datetime | None = None) -> bool:
    return (
        order.status == "pending_payment"
        and order.payment_status in ("unpaid", "failed")
        and order.payment_expires_at > (now or utcnow())
    )


def order_view(db: Session, order: Order) -> OrderOut:
    items = db.scalars(
        select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.position)
    ).all()
    events = db.scalars(
        select(OrderEvent)
        .where(OrderEvent.order_id == order.id, OrderEvent.customer_visible.is_(True))
        .order_by(OrderEvent.created_at, OrderEvent.id)
    ).all()
    shipments = db.scalars(
        select(Shipment).where(Shipment.order_id == order.id).order_by(Shipment.created_at)
    ).all()
    refunds = db.scalars(
        select(Refund).where(Refund.order_id == order.id).order_by(Refund.created_at)
    ).all()
    requests = db.scalars(
        select(ReturnRequest)
        .where(ReturnRequest.order_id == order.id)
        .order_by(ReturnRequest.created_at)
    ).all()
    # Imported here: the returns service builds on this module.
    from app.services import returns

    method = order.shipping_method
    return OrderOut(
        reference=order.reference,
        status=order.status,
        status_label=STATUS_LABELS[order.status],
        payment_status=order.payment_status,
        payment_status_label=PAYMENT_LABELS[order.payment_status],
        created_at=order.created_at,
        paid_at=order.paid_at,
        payment_expires_at=order.payment_expires_at,
        email=order.email,
        customer_name=order.customer_name,
        phone=order.phone,
        shipping_address=_address(order.shipping_address),
        billing_address=_address(order.billing_address),
        shipping_method=OrderShippingMethodOut(
            code=method["code"],
            name=method["name"],
            min_days=method["min_days"],
            max_days=method["max_days"],
            estimated_from=date.fromisoformat(method["estimated_from"]),
            estimated_to=date.fromisoformat(method["estimated_to"]),
        ),
        coupon_code=order.coupon_code,
        customer_note=order.customer_note,
        items=[
            OrderItemOut(
                position=i.position,
                product_name=i.product_name,
                product_slug=i.product_slug,
                variant_label=i.variant_label,
                sku=i.sku,
                purity=i.purity,
                image=_image(i),
                quantity=i.quantity,
                unit_price=i.unit_price,
                line_discount=i.line_discount,
                line_tax=i.line_tax,
                line_total=i.line_total,
            )
            for i in items
        ],
        totals=OrderTotalsOut(
            subtotal=order.subtotal,
            automatic_discount=order.automatic_discount,
            coupon_discount=order.coupon_discount,
            tax_total=order.tax_total,
            shipping_total=order.shipping_total,
            rounding_adjustment=order.rounding_adjustment,
            grand_total=order.grand_total,
            breakdown=[PriceRowOut(**row) for row in order.pricing_context.get("breakdown", [])],
        ),
        timeline=[
            OrderEventOut(
                kind=e.kind,
                title=EVENT_TITLES.get(e.kind, STATUS_LABELS.get(e.to_status or "", e.kind)),
                note=e.note,
                created_at=e.created_at,
            )
            for e in events
        ],
        shipments=[
            ShipmentOut(
                carrier=s.carrier,
                tracking_number=s.tracking_number,
                tracking_url=s.tracking_url,
                status=s.status,
                shipped_at=s.shipped_at,
                delivered_at=s.delivered_at,
            )
            for s in shipments
        ],
        refunds=[
            RefundOut(amount=r.amount, status=r.status, created_at=r.created_at) for r in refunds
        ],
        can_pay=can_pay(order),
        can_cancel=can_customer_cancel(order),
        payment_message=_payment_message(order),
        returns=[return_view(r) for r in requests],
        returnable_items=[
            ReturnableItemOut(
                position=r.position,
                product_name=r.product_name,
                variant_label=r.variant_label,
                quantity=r.quantity,
                kinds=r.kinds,
                deadline=r.deadline,
            )
            for r in returns.returnable_items(db, order)
        ],
    )


def return_view(request: ReturnRequest) -> ReturnOut:
    return ReturnOut(
        id=str(request.id),
        kind=request.kind,
        kind_label=RETURN_KIND_LABELS[request.kind],
        status=request.status,
        status_label=RETURN_STATUS_LABELS[request.status],
        reason=request.reason,
        store_note=request.store_note,
        items=[
            ReturnLineOut(
                position=int(line["position"]),
                product_name=line["product_name"],
                variant_label=line["variant_label"],
                quantity=int(line["quantity"]),
            )
            for line in request.items
        ],
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def list_orders(db: Session, user: User, page: int, page_size: int) -> Page[OrderSummaryOut]:
    total = db.scalar(select(func.count()).select_from(Order).where(Order.user_id == user.id)) or 0
    orders = db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc(), Order.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(selectinload(Order.items))
    ).all()
    return Page(
        items=[
            OrderSummaryOut(
                reference=o.reference,
                status=o.status,
                status_label=STATUS_LABELS[o.status],
                payment_status=o.payment_status,
                created_at=o.created_at,
                grand_total=o.grand_total,
                item_count=sum(i.quantity for i in o.items),
                first_item_name=o.items[0].product_name if o.items else "",
                image=_image(o.items[0]) if o.items else None,
            )
            for o in orders
        ],
        page=page,
        page_size=page_size,
        total=total,
        pages=max(1, -(-total // page_size)),
    )


def refundable_amount(db: Session, order: Order) -> Decimal:
    refunded = db.scalar(
        select(func.coalesce(func.sum(Refund.amount), ZERO)).where(
            Refund.order_id == order.id, Refund.status != "failed"
        )
    )
    return order.grand_total - (refunded or ZERO)
