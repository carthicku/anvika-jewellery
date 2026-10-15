"""Payments: starting a payment, verifying it, webhooks, and expiry/reconciliation.
See docs/architecture/PAYMENT_FLOW.md.

Golden rules:
* An order becomes paid ONLY through `mark_order_paid`, and only with a payment fetched from (or
  signed by) the provider whose order id, amount and currency match what we created.
* The browser's success callback is a hint, never proof. Signature + provider fetch decide.
* Every path is idempotent: verify, webhook and reconciliation can all see the same payment.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, Conflict, OutOfStock, PaymentProviderError
from app.core.money import to_paise
from app.core.time import utcnow
from app.models import Cart, Order, OrderItem, PaymentAttempt, PaymentEvent, Refund
from app.schemas.orders import PaymentPrefillOut, PaymentSessionOut
from app.services import inventory, orders
from app.services.payment_gateway import PaymentGateway, ProviderPayment, sanitise

logger = logging.getLogger("app.payments")

Outcome = Literal["paid", "processing", "failed", "review"]
SYNC_MESSAGES: dict[str, str] = {
    "paid": "Payment received — your order is confirmed.",
    "processing": "We've received your payment and are waiting for the bank to confirm it.",
    "failed": "The payment didn't go through. You can try again.",
    "review": "We received your payment but need to review your order. We'll contact you shortly.",
}


class PaymentVerificationFailed(AppError):
    status_code = 400
    code = "PAYMENT_VERIFICATION_FAILED"
    message = "We couldn't verify this payment. If money was taken, it will be reconciled."


# --------------------------------------------------------------------------------------------
# Starting a payment
# --------------------------------------------------------------------------------------------


def payment_session(
    settings: Settings, gateway: PaymentGateway, order: Order, attempt: PaymentAttempt
) -> PaymentSessionOut:
    return PaymentSessionOut(
        provider=attempt.provider,
        key_id=gateway.key_id,
        provider_order_id=attempt.provider_order_id,
        amount_paise=attempt.amount_paise,
        currency=attempt.currency,
        store_name=settings.store_name,
        description=f"Order {order.reference}",
        prefill=PaymentPrefillOut(name=order.customer_name, email=order.email, contact=order.phone),
    )


def start_payment(db: Session, gateway: PaymentGateway, order: Order) -> PaymentAttempt:
    """Create a provider order for exactly `grand_total` and record the attempt.

    Called after the order is committed, so a provider outage never loses the order: the
    customer can retry while the reservation is valid. The caller commits."""
    amount = to_paise(order.grand_total)
    provider_order = gateway.create_order(
        amount, receipt=order.reference, notes={"order_reference": order.reference}
    )
    if provider_order.amount_paise != amount or provider_order.currency != "INR":
        raise PaymentProviderError("The payment provider returned an unexpected amount.")
    attempt = PaymentAttempt(
        order_id=order.id,
        provider=gateway.name,
        provider_order_id=provider_order.id,
        amount_paise=amount,
        currency="INR",
        status="created",
    )
    db.add(attempt)
    db.flush()
    return attempt


def latest_open_attempt(db: Session, order: Order) -> PaymentAttempt | None:
    return db.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.order_id == order.id, PaymentAttempt.status == "created")
        .order_by(PaymentAttempt.created_at.desc())
        .limit(1)
    )


def retry_payment(db: Session, gateway: PaymentGateway, order: Order) -> PaymentAttempt:
    """A fresh provider order for a still-payable order. Never creates a second store order."""
    if order.status == "pending_payment" and order.payment_status == "authorized":
        raise Conflict(
            "Your payment is being confirmed by the bank. Please wait a few minutes.",
            code="PAYMENT_IN_PROGRESS",
        )
    if not orders.can_pay(order):
        raise Conflict(
            "This order can no longer be paid. Please place a new order from your cart.",
            code="ORDER_NOT_PAYABLE",
        )
    return start_payment(db, gateway, order)


def attempt_for(db: Session, order: Order, provider_order_id: str) -> PaymentAttempt:
    attempt = db.scalar(
        select(PaymentAttempt).where(
            PaymentAttempt.order_id == order.id,
            PaymentAttempt.provider_order_id == provider_order_id,
        )
    )
    if attempt is None:
        raise PaymentVerificationFailed("This payment doesn't belong to this order.")
    return attempt


# --------------------------------------------------------------------------------------------
# Applying provider payment facts to an order
# --------------------------------------------------------------------------------------------


@dataclass
class SyncResult:
    outcome: Outcome
    order: Order


def _matches(attempt: PaymentAttempt, payment: ProviderPayment) -> bool:
    return (
        payment.order_id == attempt.provider_order_id
        and payment.amount_paise == attempt.amount_paise
        and payment.currency == "INR"
    )


def _confirm(db: Session, settings: Settings, order: Order, source: str) -> Outcome:
    """Stock is committed and the order confirmed (late captures re-reserve first)."""
    if order.status in ("expired", "cancelled"):
        # Late capture. An order that simply ran out of time is confirmed if every piece can be
        # reserved again; a cancelled or replaced order always goes to a person.
        if order.status == "expired" and not order.pricing_context.get("superseded"):
            items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
            lines = [(i.variant_id, i.quantity) for i in items if i.variant_id is not None]
            reserved = False
            if lines and len(lines) == len(items):
                try:
                    with db.begin_nested():
                        inventory.reserve(db, order.id, lines, utcnow())
                    reserved = True
                except OutOfStock:
                    reserved = False
            if reserved:
                inventory.commit(db, order.id)
                orders.set_redemption_status(db, order, "redeemed")
                orders.transition(
                    db,
                    order,
                    "confirmed",
                    kind="order_confirmed",
                    actor_type="provider",
                    note="Payment arrived after the payment window; your pieces were still "
                    "available.",
                )
                _after_confirmed(db, settings, order)
                return "paid"
        orders.add_event(
            db,
            order,
            "late_capture",
            actor_type="provider",
            note=f"Captured payment for a {order.status} order (via {source}) — refund or fulfil.",
            customer_visible=False,
        )
        orders.transition(db, order, "payment_review", kind="payment_review", actor_type="provider")
        return "review"
    if order.status == "pending_payment":
        inventory.commit(db, order.id)
        orders.set_redemption_status(db, order, "redeemed")
        orders.transition(db, order, "confirmed", kind="order_confirmed", actor_type="provider")
        _after_confirmed(db, settings, order)
        return "paid"
    # payment_review or later: money recorded, status left for the admin.
    return "review" if order.status == "payment_review" else "paid"


def _after_confirmed(db: Session, settings: Settings, order: Order) -> None:
    if order.cart_id is not None:
        cart = db.get(Cart, order.cart_id)
        if cart is not None and cart.status == "active":
            cart.status = "converted"
    orders.queue_email(
        db, settings, order, "order_confirmation", "Your order {reference} is confirmed"
    )


def mark_order_paid(
    db: Session,
    settings: Settings,
    order_id: uuid.UUID,
    attempt: PaymentAttempt,
    payment: ProviderPayment,
    source: str,
) -> SyncResult:
    """THE transition to paid. Idempotent; locks the order row; caller commits."""
    order = orders.lock_order(db, order_id)
    if payment.status != "captured" or not _matches(attempt, payment):
        raise PaymentVerificationFailed()
    if attempt.status == "captured" and attempt.provider_payment_id == payment.id:
        return SyncResult("review" if order.status == "payment_review" else "paid", order)

    if order.payment_status in ("paid", "refund_pending", "partially_refunded", "refunded"):
        # A second, different capture for an order that is already paid: record it and ask an
        # admin to refund it. We never keep duplicate money silently.
        _record_capture(attempt, payment)
        db.add(
            Refund(
                order_id=order.id,
                payment_attempt_id=attempt.id,
                amount=order.grand_total,
                status="requested",
                reason=f"Duplicate payment {payment.id} via {source}",
            )
        )
        orders.add_event(
            db,
            order,
            "duplicate_payment",
            actor_type="provider",
            note=f"Additional payment {payment.id} captured; refund requested",
            customer_visible=False,
        )
        return SyncResult("paid", order)

    _record_capture(attempt, payment)
    order.payment_status = "paid"
    order.paid_at = utcnow()
    orders.add_event(
        db,
        order,
        "payment_captured",
        actor_type="provider",
        note=f"{payment.method or 'payment'} via {source}",
        customer_visible=False,
    )
    outcome = _confirm(db, settings, order, source)
    db.flush()
    return SyncResult(outcome, order)


def _record_capture(attempt: PaymentAttempt, payment: ProviderPayment) -> None:
    attempt.status = "captured"
    attempt.provider_payment_id = payment.id
    attempt.method = payment.method
    attempt.error_code = None
    attempt.error_description = None


def sync_payment(
    db: Session,
    settings: Settings,
    order_id: uuid.UUID,
    attempt: PaymentAttempt,
    payment: ProviderPayment,
    source: str,
) -> SyncResult:
    """Apply whatever the provider says about one payment to its order."""
    if payment.order_id != attempt.provider_order_id:
        raise PaymentVerificationFailed("This payment doesn't belong to this order.")
    if payment.status == "refunded":  # refunds are tracked through Refund records
        order = orders.lock_order(db, order_id)
        return SyncResult("paid" if order.paid_at else "failed", order)
    if payment.status == "captured":
        if not _matches(attempt, payment):
            order = orders.lock_order(db, order_id)
            logger.error("Payment %s does not match attempt %s", payment.id, attempt.id)
            orders.add_event(
                db,
                order,
                "payment_mismatch",
                actor_type="provider",
                note=f"Payment {payment.id} amount/currency does not match — needs review",
                customer_visible=False,
            )
            raise PaymentVerificationFailed()
        return mark_order_paid(db, settings, order_id, attempt, payment, source)

    order = orders.lock_order(db, order_id)
    if payment.status == "authorized":
        if attempt.status == "created":
            attempt.status = "authorized"
            attempt.provider_payment_id = payment.id
            attempt.method = payment.method
        if order.payment_status in ("unpaid", "failed"):
            order.payment_status = "authorized"
            orders.add_event(db, order, "payment_authorized", actor_type="provider")
        return SyncResult("processing", order)

    if payment.status == "failed":
        if attempt.status in ("created", "authorized"):
            attempt.status = "failed"
            attempt.provider_payment_id = attempt.provider_payment_id or payment.id
            attempt.error_code = payment.error_code
            attempt.error_description = (payment.error_description or "")[:300] or None
        if order.payment_status in ("unpaid", "authorized") and order.status == "pending_payment":
            order.payment_status = "failed"
            orders.add_event(
                db,
                order,
                "payment_failed",
                actor_type="provider",
                note=payment.error_description,
            )
        return SyncResult("failed" if order.payment_status != "paid" else "paid", order)

    return SyncResult("processing", order)  # "created": the customer hasn't finished paying


def verify_checkout(
    db: Session,
    settings: Settings,
    gateway: PaymentGateway,
    order: Order,
    provider_order_id: str,
    provider_payment_id: str,
    signature: str,
) -> SyncResult:
    """Browser success callback → signature check against OUR stored provider order id → fetch
    the payment from the provider → apply it."""
    attempt = attempt_for(db, order, provider_order_id)
    if not gateway.verify_checkout_signature(
        attempt.provider_order_id, provider_payment_id, signature
    ):
        logger.warning("Invalid checkout signature for order %s", order.reference)
        orders.add_event(
            db,
            order,
            "payment_signature_invalid",
            actor_type="system",
            note=f"Rejected signature for payment {provider_payment_id[:40]}",
            customer_visible=False,
        )
        db.commit()
        raise PaymentVerificationFailed()
    payment = gateway.fetch_payment(provider_payment_id)
    return sync_payment(db, settings, order.id, attempt, payment, "checkout")


def report_failure(
    db: Session,
    settings: Settings,
    gateway: PaymentGateway,
    order: Order,
    provider_order_id: str,
    provider_payment_id: str | None,
) -> SyncResult:
    """The pop-up reported a failure. We record only what the provider confirms."""
    attempt = attempt_for(db, order, provider_order_id)
    if provider_payment_id:
        payment = gateway.fetch_payment(provider_payment_id)
        return sync_payment(db, settings, order.id, attempt, payment, "checkout")
    return SyncResult("failed", orders.lock_order(db, order.id))


# --------------------------------------------------------------------------------------------
# Webhooks
# --------------------------------------------------------------------------------------------


def store_webhook_event(
    db: Session, event_id: str, event_type: str, payload: dict[str, Any]
) -> PaymentEvent | None:
    """Insert the event once. Returns None when this event id was already received."""
    stmt = (
        insert(PaymentEvent)
        .values(
            id=uuid.uuid4(),
            provider="razorpay",
            event_id=event_id,
            event_type=event_type[:60],
            payload=payload,
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
        .returning(PaymentEvent.id)
    )
    new_id = db.execute(stmt).scalar()
    return db.get(PaymentEvent, new_id) if new_id else None


def event_id_for(header_value: str | None, raw_body: bytes) -> str:
    return (header_value or "").strip()[:100] or "sha256:" + hashlib.sha256(raw_body).hexdigest()


def sanitised_payload(body: dict[str, Any]) -> dict[str, Any]:
    payload = body.get("payload") or {}
    return {
        "event": body.get("event"),
        "created_at": body.get("created_at"),
        "payment": sanitise((payload.get("payment") or {}).get("entity")),
        "order": sanitise((payload.get("order") or {}).get("entity")),
        "refund": sanitise((payload.get("refund") or {}).get("entity")),
    }


def process_webhook(
    db: Session, settings: Settings, event: PaymentEvent, body: dict[str, Any]
) -> str:
    """Apply a verified webhook. Returns a short note stored on the event."""
    kind = str(body.get("event", ""))
    payload = body.get("payload") or {}
    if kind in ("payment.authorized", "payment.captured", "payment.failed", "order.paid"):
        entity = (payload.get("payment") or {}).get("entity")
        if not entity:
            return "no payment entity"
        payment = ProviderPayment.from_entity(entity)
        attempt = db.scalar(
            select(PaymentAttempt).where(PaymentAttempt.provider_order_id == payment.order_id)
        )
        if attempt is None:
            return "unknown provider order"
        result = sync_payment(db, settings, attempt.order_id, attempt, payment, "webhook")
        return f"order {result.order.reference}: {result.outcome}"
    if kind in ("refund.processed", "refund.failed"):
        entity = (payload.get("refund") or {}).get("entity") or {}
        refund = db.scalar(select(Refund).where(Refund.provider_refund_id == entity.get("id")))
        if refund is None:
            return "unknown refund"
        apply_refund_status(db, refund, "processed" if kind == "refund.processed" else "failed")
        return f"refund {refund.id}: {refund.status}"
    return "ignored"


def apply_refund_status(db: Session, refund: Refund, status: str) -> None:
    order = orders.lock_order(db, refund.order_id)
    if refund.status in ("processed", "failed"):
        return
    refund.status = status
    if status == "processed":
        remaining = orders.refundable_amount(db, order)
        processed_all = remaining <= 0
        order.payment_status = "refunded" if processed_all else "partially_refunded"
        orders.add_event(db, order, "refund_processed", actor_type="provider")


# --------------------------------------------------------------------------------------------
# Expiry and reconciliation (background job + `python -m app.cli reconcile-payments`)
# --------------------------------------------------------------------------------------------


@dataclass
class ReconcileReport:
    checked: int = 0
    paid: int = 0
    expired: int = 0
    review: int = 0
    errors: int = 0


def _provider_payments(
    gateway: PaymentGateway, attempts: list[PaymentAttempt]
) -> list[tuple[PaymentAttempt, ProviderPayment]]:
    found = []
    for attempt in attempts:
        for payment in gateway.payments_for_order(attempt.provider_order_id):
            found.append((attempt, payment))
    return found


def reconcile_order(
    db: Session, settings: Settings, gateway: PaymentGateway, order: Order, now: datetime
) -> str:
    """Ask the provider about every attempt of a pending order; confirm, expire or wait."""
    attempts = list(
        db.scalars(select(PaymentAttempt).where(PaymentAttempt.order_id == order.id)).all()
    )
    payments = _provider_payments(gateway, attempts)
    captured = [(a, p) for a, p in payments if p.status == "captured"]
    if captured:
        attempt, payment = captured[0]
        return sync_payment(db, settings, order.id, attempt, payment, "reconciliation").outcome
    authorized = [(a, p) for a, p in payments if p.status == "authorized"]
    for attempt, payment in authorized:
        sync_payment(db, settings, order.id, attempt, payment, "reconciliation")
    for attempt, payment in payments:
        if payment.status == "failed":
            sync_payment(db, settings, order.id, attempt, payment, "reconciliation")
    if order.payment_expires_at > now:
        return "waiting"
    if authorized:
        # Money is held but not captured past the window: a person decides.
        orders.transition(
            db,
            order,
            "payment_review",
            kind="payment_review",
            actor_type="system",
            note="Payment authorised but not captured before the payment window closed.",
        )
        return "review"
    inventory.release(db, order.id, note=f"Order {order.reference} payment window closed")
    orders.set_redemption_status(db, order, "released")
    orders.transition(db, order, "expired", kind="order_expired", actor_type="system")
    return "expired"


def expire_and_reconcile(
    db: Session,
    settings: Settings,
    gateway: PaymentGateway,
    *,
    now: datetime | None = None,
    include_unexpired: bool = False,
    limit: int = 50,
) -> ReconcileReport:
    """Process overdue pending orders (and, with include_unexpired, all pending ones). Each order
    is its own transaction, locked with SKIP LOCKED so several workers never collide. A provider
    error leaves the order untouched for the next run — we never expire what we couldn't check."""
    now = now or utcnow()
    report = ReconcileReport()
    stmt = select(Order.id).where(Order.status == "pending_payment")
    if not include_unexpired:
        stmt = stmt.where(Order.payment_expires_at < now)
    order_ids = list(db.scalars(stmt.order_by(Order.payment_expires_at).limit(limit)).all())
    db.rollback()
    for order_id in order_ids:
        order = db.scalar(
            select(Order)
            .where(Order.id == order_id, Order.status == "pending_payment")
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if order is None:
            db.rollback()
            continue
        report.checked += 1
        try:
            result = reconcile_order(db, settings, gateway, order, now)
            db.commit()
        except (PaymentProviderError, PaymentVerificationFailed) as exc:
            db.rollback()
            report.errors += 1
            logger.warning("Reconciliation skipped order %s: %s", order_id, exc.code)
            continue
        if result == "paid":
            report.paid += 1
        elif result == "expired":
            report.expired += 1
        elif result == "review":
            report.review += 1
    return report


def describe(report: ReconcileReport) -> str:
    return json.dumps(report.__dict__)
