"""Payment verification, failure reports, retries, the development simulator and the Razorpay
webhook. An order is marked paid only by app.services.payments.mark_order_paid."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import (
    Auth,
    get_app_settings,
    get_gateway,
    get_optional_auth,
    get_order_access_token,
)
from app.api.v1.routes.auth import send_emails_later
from app.core.config import Settings
from app.core.db import get_db
from app.core.errors import BadRequest, NotFound
from app.core.rate_limit import rate_limit
from app.core.time import utcnow
from app.schemas.orders import (
    PaymentFailureIn,
    PaymentResultOut,
    RetryPaymentIn,
    RetryPaymentOut,
    SimulatorPayIn,
    SimulatorPayOut,
    VerifyPaymentIn,
)
from app.services import orders, payments
from app.services.payment_gateway import PaymentGateway, SimulatorGateway, verify_webhook_signature
from app.services.payments import PaymentVerificationFailed, SyncResult

logger = logging.getLogger("app.payments")
router = APIRouter(prefix="/payments", tags=["payments"])
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_verify_limit = Depends(rate_limit("payments-ip", limit=60, window_seconds=600))


def _result(
    db: Session, request: Request, tasks: BackgroundTasks, result: SyncResult
) -> PaymentResultOut:
    out = PaymentResultOut(
        outcome=result.outcome,
        message=payments.SYNC_MESSAGES[result.outcome],
        order=orders.order_view(db, result.order),
    )
    db.commit()  # end the read transaction before the after-response work
    send_emails_later(request, tasks)  # e.g. the order confirmation
    return out


@router.post("/verify", response_model=PaymentResultOut, dependencies=[_verify_limit])
def verify_payment(
    data: VerifyPaymentIn,
    request: Request,
    response: Response,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    gateway: PaymentGateway = Depends(get_gateway),
    auth: Auth | None = Depends(get_optional_auth),
    access_token: str | None = Depends(get_order_access_token),
) -> PaymentResultOut:
    """Called by the checkout page after the payment pop-up reports success. The signature is
    checked against the provider order id WE stored, then the payment is fetched from the
    provider; only a captured payment for the exact amount confirms the order."""
    response.headers["Cache-Control"] = "no-store"
    order = orders.find_order(db, data.reference, auth.user if auth else None, access_token)
    result = payments.verify_checkout(
        db,
        settings,
        gateway,
        order,
        data.provider_order_id,
        data.provider_payment_id,
        data.signature,
    )
    db.commit()
    return _result(db, request, tasks, result)


@router.post("/report-failure", response_model=PaymentResultOut, dependencies=[_verify_limit])
def report_failure(
    data: PaymentFailureIn,
    request: Request,
    response: Response,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    gateway: PaymentGateway = Depends(get_gateway),
    auth: Auth | None = Depends(get_optional_auth),
    access_token: str | None = Depends(get_order_access_token),
) -> PaymentResultOut:
    """The pop-up reported a failure. Only what the provider confirms is recorded."""
    response.headers["Cache-Control"] = "no-store"
    order = orders.find_order(db, data.reference, auth.user if auth else None, access_token)
    result = payments.report_failure(
        db, settings, gateway, order, data.provider_order_id, data.provider_payment_id
    )
    db.commit()
    return _result(db, request, tasks, result)


@router.post("/retry", response_model=RetryPaymentOut, dependencies=[_verify_limit])
def retry_payment(
    data: RetryPaymentIn,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    gateway: PaymentGateway = Depends(get_gateway),
    auth: Auth | None = Depends(get_optional_auth),
    access_token: str | None = Depends(get_order_access_token),
) -> RetryPaymentOut:
    """A new payment for a still-pending order (same order, same amount, stock still held)."""
    response.headers["Cache-Control"] = "no-store"
    order = orders.find_order(
        db, data.reference, auth.user if auth else None, access_token, lock=True
    )
    attempt = payments.retry_payment(db, gateway, order)
    db.commit()
    return RetryPaymentOut(
        order=orders.order_view(db, order),
        payment=payments.payment_session(settings, gateway, order, attempt),
    )


@router.post("/simulator/pay", response_model=SimulatorPayOut, dependencies=[_verify_limit])
def simulator_pay(
    data: SimulatorPayIn,
    db: Session = Depends(get_db),
    gateway: PaymentGateway = Depends(get_gateway),
    auth: Auth | None = Depends(get_optional_auth),
    access_token: str | None = Depends(get_order_access_token),
) -> SimulatorPayOut:
    """DEVELOPMENT/TEST ONLY: what the payment pop-up would return. No money moves. Returns 404
    unless PAYMENT_PROVIDER=simulator (which production settings refuse)."""
    if not isinstance(gateway, SimulatorGateway):
        raise NotFound()
    order = orders.find_order(db, data.reference, auth.user if auth else None, access_token)
    attempt = payments.attempt_for(db, order, data.provider_order_id)
    outcome = "captured" if data.outcome == "success" else "failed"
    payment, signature = gateway.simulate_payment(
        attempt.provider_order_id, attempt.amount_paise, outcome
    )
    return SimulatorPayOut(
        provider_order_id=attempt.provider_order_id,
        provider_payment_id=payment.id,
        signature=signature if outcome == "captured" else None,
        status=payment.status,
    )


# --------------------------------------------------------------------------------------------
# Razorpay webhook (CSRF-exempt; authenticated by HMAC over the raw body)
# --------------------------------------------------------------------------------------------


def _handle_webhook(
    db: Session, settings: Settings, event_id: str, body: dict[str, object]
) -> dict[str, str]:
    event_type = str(body.get("event", ""))
    event = payments.store_webhook_event(db, event_id, event_type, payments.sanitised_payload(body))
    if event is None:
        db.rollback()
        return {"status": "duplicate"}
    try:
        note = payments.process_webhook(db, settings, event, body)
    except PaymentVerificationFailed as exc:
        # The payment doesn't match what we created; retrying won't change that. Keep the event
        # (with the error) for the admin and acknowledge it.
        db.rollback()
        event = payments.store_webhook_event(
            db, event_id, event_type, payments.sanitised_payload(body)
        )
        if event is not None:
            event.processing_error = exc.message
            event.processed_at = utcnow()
        db.commit()
        logger.error("Webhook %s rejected: %s", event_id, exc.message)
        return {"status": "rejected"}
    event.processed_at = utcnow()
    event.processing_error = None
    db.commit()
    logger.info("Webhook %s (%s): %s", event_id, event_type, note)
    return {"status": "processed"}


@webhook_router.post("/razorpay", include_in_schema=False)
async def razorpay_webhook(
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, str]:
    raw = await request.body()
    secret = settings.razorpay_webhook_secret.get_secret_value()
    if not verify_webhook_signature(secret, raw, request.headers.get("X-Razorpay-Signature")):
        logger.warning("Rejected webhook with an invalid signature")
        raise BadRequest("Invalid signature.", code="WEBHOOK_SIGNATURE_INVALID")
    try:
        body = json.loads(raw)
    except ValueError as exc:
        raise BadRequest("Invalid JSON.", code="WEBHOOK_INVALID") from exc
    if not isinstance(body, dict):
        raise BadRequest("Invalid JSON.", code="WEBHOOK_INVALID")
    event_id = payments.event_id_for(request.headers.get("x-razorpay-event-id"), raw)
    # Any other error → 500, nothing stored, and Razorpay retries the delivery later.
    result = await run_in_threadpool(_handle_webhook, db, settings, event_id, body)
    send_emails_later(request, tasks)
    return result
