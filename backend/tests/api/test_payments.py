"""Payments: verification, forged signatures, failures and retries, webhooks, expiry and
reconciliation, late captures, cancellations and the Razorpay REST client (J3–J6, J11)."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import PaymentProviderError
from app.core.time import utcnow
from app.models import (
    Cart,
    CouponRedemption,
    InventoryMovement,
    InventoryReservation,
    Order,
    PaymentAttempt,
    PaymentEvent,
    Refund,
)
from app.services import payments
from app.services.email import MEMORY_OUTBOX
from app.services.payment_gateway import (
    RazorpayGateway,
    SimulatorGateway,
    hmac_sha256,
    verify_webhook_signature,
)
from tests.api.order_helpers import (
    add_to_cart,
    buy,
    level,
    place_order,
    simulate,
    token_headers,
    verify,
)

SKU = "ANV-RG-002-12"
WEBHOOK_SECRET = "whsec_test_0123456789abcdef"


def checkout(client: TestClient, db: Session, sku: str = SKU, quantity: int = 1) -> dict[str, Any]:
    add_to_cart(client, db, sku, quantity)
    response = place_order(client)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def get_order(db: Session, reference: str) -> Order:
    order = db.scalar(
        select(Order).where(Order.reference == reference).execution_options(populate_existing=True)
    )
    assert order is not None
    return order


def sim(app: FastAPI) -> SimulatorGateway:
    gateway = app.state.payment_gateway
    assert isinstance(gateway, SimulatorGateway)
    return gateway


# ------------------------------------------------------------------ happy path


def test_verified_payment_confirms_order_and_sells_stock(client: TestClient, db: Session) -> None:
    before = level(db, SKU)
    on_hand, reserved = before.on_hand, before.reserved
    body = checkout(client, db, quantity=2)
    result = verify(client, body, simulate(client, body))
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["outcome"] == "paid"
    order = data["order"]
    assert order["status"] == "confirmed" and order["payment_status"] == "paid"
    assert order["paid_at"] is not None
    assert order["can_pay"] is False and order["can_cancel"] is True
    assert [e["kind"] for e in order["timeline"]] == ["order_created", "order_confirmed"]
    after = level(db, SKU)
    assert (after.on_hand, after.reserved) == (on_hand - 2, reserved)
    sale = db.scalars(select(InventoryMovement).where(InventoryMovement.reason == "sale")).all()
    assert [(m.delta_on_hand, m.delta_reserved) for m in sale] == [(-2, -2)]
    cart = db.scalar(select(Cart).execution_options(populate_existing=True))
    assert cart is not None and cart.status == "converted"
    assert client.get("/api/v1/cart").json()["item_count"] == 0
    # Confirmation email with the private order link.
    assert len(MEMORY_OUTBOX) == 1
    message = MEMORY_OUTBOX[0]
    assert message["To"] == "guest@example.com"
    assert order["reference"] in message["Subject"]
    text = message.get_body(("plain",)).get_content()  # type: ignore[union-attr]
    assert f"/order-confirmation/{order['reference']}#token=" in text


def test_verifying_twice_is_harmless(client: TestClient, db: Session) -> None:
    body = checkout(client, db)
    payment = simulate(client, body)
    assert verify(client, body, payment).json()["outcome"] == "paid"
    again = verify(client, body, payment)
    assert again.status_code == 200 and again.json()["outcome"] == "paid"
    assert (
        db.scalar(
            select(func.count())
            .select_from(InventoryMovement)
            .where(InventoryMovement.reason == "sale")
        )
        == 1
    )
    assert len(MEMORY_OUTBOX) == 1


def test_coupon_redemption_is_confirmed_on_payment(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU)
    client.post("/api/v1/cart/coupon", json={"code": "WELCOME5"})
    body = place_order(client).json()
    verify(client, body, simulate(client, body))
    redemption = db.scalar(select(CouponRedemption).execution_options(populate_existing=True))
    assert redemption is not None and redemption.status == "redeemed"


# ------------------------------------------------------------------ tampering


def test_forged_signature_is_rejected(client: TestClient, db: Session) -> None:
    body = checkout(client, db)
    payment = simulate(client, body)
    forged = {**payment, "signature": "0" * 64}
    response = verify(client, body, forged)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PAYMENT_VERIFICATION_FAILED"
    order = get_order(db, body["order"]["reference"])
    assert order.status == "pending_payment" and order.payment_status == "unpaid"


def test_payment_for_another_order_cannot_pay_this_one(
    client: TestClient, other_client: TestClient, db: Session
) -> None:
    cheap = checkout(other_client, db, "ANV-PD-001")
    cheap_payment = simulate(other_client, cheap)
    mine = checkout(client, db)
    # Valid signature, but for a different provider order → not accepted for this order.
    response = verify(client, mine, cheap_payment)
    assert response.status_code == 400
    assert get_order(db, mine["order"]["reference"]).payment_status == "unpaid"


def test_signature_is_checked_against_the_stored_provider_order(
    client: TestClient, db: Session, app: FastAPI
) -> None:
    body = checkout(client, db)
    gateway = sim(app)
    # A "payment" signed for a provider order we never created for this order.
    payment, signature = gateway.simulate_payment("order_sim_00000000000000", 100, "captured")
    response = client.post(
        "/api/v1/payments/verify",
        json={
            "reference": body["order"]["reference"],
            "provider_order_id": body["payment"]["provider_order_id"],
            "provider_payment_id": payment.id,
            "signature": signature,
        },
        headers=token_headers(body),
    )
    assert response.status_code == 400
    assert get_order(db, body["order"]["reference"]).payment_status == "unpaid"


def test_amount_mismatch_never_marks_paid(client: TestClient, db: Session, app: FastAPI) -> None:
    body = checkout(client, db)
    provider_order = body["payment"]["provider_order_id"]
    gateway = sim(app)
    payment, signature = gateway.simulate_payment(provider_order, 100, "captured")  # ₹1
    response = client.post(
        "/api/v1/payments/verify",
        json={
            "reference": body["order"]["reference"],
            "provider_order_id": provider_order,
            "provider_payment_id": payment.id,
            "signature": signature,
        },
        headers=token_headers(body),
    )
    assert response.status_code == 400
    assert get_order(db, body["order"]["reference"]).payment_status == "unpaid"


def test_guest_cannot_verify_without_the_order_token(
    client: TestClient, other_client: TestClient, db: Session
) -> None:
    body = checkout(client, db)
    payment = simulate(client, body)
    response = other_client.post(
        "/api/v1/payments/verify",
        json={
            "reference": body["order"]["reference"],
            "provider_order_id": payment["provider_order_id"],
            "provider_payment_id": payment["provider_payment_id"],
            "signature": payment["signature"],
        },
    )
    assert response.status_code == 404


# ------------------------------------------------------------------ failure, retry, authorised


def test_failed_payment_can_be_retried(client: TestClient, db: Session) -> None:
    body = checkout(client, db)
    failed = simulate(client, body, "failure")
    assert failed["signature"] is None
    response = client.post(
        "/api/v1/payments/report-failure",
        json={
            "reference": body["order"]["reference"],
            "provider_order_id": failed["provider_order_id"],
            "provider_payment_id": failed["provider_payment_id"],
        },
        headers=token_headers(body),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "failed"
    assert data["order"]["payment_status"] == "failed"
    assert data["order"]["status"] == "pending_payment"
    assert data["order"]["can_pay"] is True
    assert data["order"]["timeline"][-1]["kind"] == "payment_failed"

    retry = client.post(
        "/api/v1/payments/retry",
        json={"reference": body["order"]["reference"]},
        headers=token_headers(body),
    )
    assert retry.status_code == 200, retry.text
    second = {**body, "payment": retry.json()["payment"]}
    assert second["payment"]["provider_order_id"] != body["payment"]["provider_order_id"]
    assert second["payment"]["amount_paise"] == body["payment"]["amount_paise"]
    assert verify(client, second, simulate(client, second)).json()["outcome"] == "paid"
    assert db.scalar(select(func.count()).select_from(Order)) == 1


def test_retry_refused_once_paid(client: TestClient, db: Session) -> None:
    body = buy(client, db)
    response = client.post(
        "/api/v1/payments/retry",
        json={"reference": body["order"]["reference"]},
        headers=token_headers(body),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_NOT_PAYABLE"


def test_authorised_payment_is_completed_by_reconciliation(
    client: TestClient, db: Session, app: FastAPI, settings: Settings
) -> None:
    body = checkout(client, db)
    gateway = sim(app)
    provider_order = body["payment"]["provider_order_id"]
    payment, signature = gateway.simulate_payment(
        provider_order, body["payment"]["amount_paise"], "authorized"
    )
    result = client.post(
        "/api/v1/payments/verify",
        json={
            "reference": body["order"]["reference"],
            "provider_order_id": provider_order,
            "provider_payment_id": payment.id,
            "signature": signature,
        },
        headers=token_headers(body),
    ).json()
    assert result["outcome"] == "processing"
    assert result["order"]["payment_status"] == "authorized"
    assert result["order"]["can_cancel"] is False  # money is in flight

    gateway.capture_later(payment.id)  # the provider captures it
    db.commit()
    report = payments.expire_and_reconcile(db, settings, gateway, include_unexpired=True)
    assert report.paid == 1
    order = get_order(db, body["order"]["reference"])
    assert (order.status, order.payment_status) == ("confirmed", "paid")


def test_simulator_endpoint_is_unavailable_with_a_real_provider(
    client: TestClient, db: Session, app: FastAPI
) -> None:
    body = checkout(client, db)
    app.state.payment_gateway = RazorpayGateway("rzp_test_x", "secret-value")
    response = client.post(
        "/api/v1/payments/simulator/pay",
        json={
            "reference": body["order"]["reference"],
            "provider_order_id": body["payment"]["provider_order_id"],
            "outcome": "success",
        },
        headers=token_headers(body),
    )
    assert response.status_code == 404


# ------------------------------------------------------------------ webhooks


def _webhook(
    client: TestClient, payload: dict[str, Any], *, event_id: str, secret: str = WEBHOOK_SECRET
):  # type: ignore[no-untyped-def]
    raw = json.dumps(payload).encode()
    return client.post(
        "/api/v1/webhooks/razorpay",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": hmac_sha256(secret, raw),
            "x-razorpay-event-id": event_id,
        },
    )


def _captured_event(order_id: str, payment_id: str, amount: int) -> dict[str, Any]:
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "amount": amount,
                    "currency": "INR",
                    "status": "captured",
                    "method": "card",
                    "card": {"last4": "1111", "network": "Visa"},
                    "email": "guest@example.com",
                }
            }
        },
    }


def _with_webhook_secret(app: FastAPI, settings: Settings) -> None:
    app.state.settings = settings.model_copy(
        update={"razorpay_webhook_secret": SecretStr(WEBHOOK_SECRET)}
    )


def test_webhook_with_bad_signature_is_rejected_and_not_stored(
    raw_client: TestClient, app: FastAPI, settings: Settings, db: Session
) -> None:
    _with_webhook_secret(app, settings)
    response = _webhook(
        raw_client, {"event": "payment.captured"}, event_id="evt_1", secret="wrong-secret-value"
    )
    assert response.status_code == 400
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


def test_webhook_capture_confirms_once_and_ignores_duplicates(
    client: TestClient, raw_client: TestClient, app: FastAPI, settings: Settings, db: Session
) -> None:
    _with_webhook_secret(app, settings)
    body = checkout(client, db)
    payment, _ = sim(app).simulate_payment(
        body["payment"]["provider_order_id"], body["payment"]["amount_paise"], "captured"
    )
    event = _captured_event(payment.order_id or "", payment.id, payment.amount_paise)
    first = _webhook(raw_client, event, event_id="evt_capture_1")
    assert first.status_code == 200 and first.json() == {"status": "processed"}
    duplicate = _webhook(raw_client, event, event_id="evt_capture_1")
    assert duplicate.json() == {"status": "duplicate"}
    # A *different* event about the same payment (e.g. order.paid) is also a no-op.
    other = _webhook(raw_client, {**event, "event": "order.paid"}, event_id="evt_order_paid")
    assert other.json() == {"status": "processed"}

    order = get_order(db, body["order"]["reference"])
    assert (order.status, order.payment_status) == ("confirmed", "paid")
    assert (
        db.scalar(
            select(func.count())
            .select_from(InventoryMovement)
            .where(InventoryMovement.reason == "sale")
        )
        == 1
    )
    stored = db.scalar(select(PaymentEvent).where(PaymentEvent.event_id == "evt_capture_1"))
    assert stored is not None and stored.processed_at is not None
    # Card details and contact info are never stored.
    assert "last4" not in json.dumps(stored.payload)
    assert "email" not in stored.payload["payment"]
    # Browser verification afterwards is also harmless.
    sim_result = {
        "provider_order_id": body["payment"]["provider_order_id"],
        "provider_payment_id": payment.id,
        "signature": hmac_sha256(
            settings.simulator_secret.get_secret_value(),
            f"{body['payment']['provider_order_id']}|{payment.id}",
        ),
    }
    assert verify(client, body, sim_result).json()["outcome"] == "paid"


def test_webhook_with_wrong_amount_is_recorded_but_not_applied(
    client: TestClient, raw_client: TestClient, app: FastAPI, settings: Settings, db: Session
) -> None:
    _with_webhook_secret(app, settings)
    body = checkout(client, db)
    event = _captured_event(body["payment"]["provider_order_id"], "pay_fake_1", 100)
    response = _webhook(raw_client, event, event_id="evt_bad_amount")
    assert response.status_code == 200 and response.json() == {"status": "rejected"}
    assert get_order(db, body["order"]["reference"]).payment_status == "unpaid"
    stored = db.scalar(select(PaymentEvent).where(PaymentEvent.event_id == "evt_bad_amount"))
    assert stored is not None and stored.processing_error


def test_webhook_failure_marks_payment_failed(
    client: TestClient, raw_client: TestClient, app: FastAPI, settings: Settings, db: Session
) -> None:
    _with_webhook_secret(app, settings)
    body = checkout(client, db)
    event = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_failed_1",
                    "order_id": body["payment"]["provider_order_id"],
                    "amount": body["payment"]["amount_paise"],
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment was declined by the bank",
                }
            }
        },
    }
    assert _webhook(raw_client, event, event_id="evt_failed").status_code == 200
    order = get_order(db, body["order"]["reference"])
    assert (order.status, order.payment_status) == ("pending_payment", "failed")


def test_webhook_signature_helper() -> None:
    raw = b'{"a":1}'
    assert verify_webhook_signature("s" * 16, raw, hmac_sha256("s" * 16, raw))
    assert not verify_webhook_signature("s" * 16, raw + b" ", hmac_sha256("s" * 16, raw))
    assert not verify_webhook_signature("", raw, hmac_sha256("", raw))
    assert not verify_webhook_signature("s" * 16, raw, None)


# ------------------------------------------------------------------ expiry and late capture


def _expire(db: Session, reference: str) -> None:
    db.execute(
        update(Order)
        .where(Order.reference == reference)
        .values(payment_expires_at=utcnow() - timedelta(minutes=1))
    )
    db.commit()


def test_unpaid_order_expires_and_releases_stock_and_coupon(
    client: TestClient, db: Session, app: FastAPI, settings: Settings
) -> None:
    add_to_cart(client, db, SKU)
    client.post("/api/v1/cart/coupon", json={"code": "WELCOME5"})
    reserved = level(db, SKU).reserved
    body = place_order(client).json()
    assert level(db, SKU).reserved == reserved + 1
    _expire(db, body["order"]["reference"])

    report = payments.expire_and_reconcile(db, settings, sim(app))
    assert (report.checked, report.expired) == (1, 1)
    order = get_order(db, body["order"]["reference"])
    assert order.status == "expired"
    assert level(db, SKU).reserved == reserved
    redemption = db.scalar(select(CouponRedemption).execution_options(populate_existing=True))
    assert redemption is not None and redemption.status == "released"
    view = client.get(
        f"/api/v1/orders/{body['order']['reference']}", headers=token_headers(body)
    ).json()
    assert view["can_pay"] is False
    assert view["status_label"] == "Payment not completed"
    # Running again changes nothing.
    assert payments.expire_and_reconcile(db, settings, sim(app)).checked == 0


def test_expiry_job_finds_a_captured_payment_first(
    client: TestClient, db: Session, app: FastAPI, settings: Settings
) -> None:
    body = checkout(client, db)
    simulate(client, body)  # paid in the pop-up, but the browser never called /verify
    _expire(db, body["order"]["reference"])
    report = payments.expire_and_reconcile(db, settings, sim(app))
    assert report.paid == 1 and report.expired == 0
    assert get_order(db, body["order"]["reference"]).status == "confirmed"


def test_provider_outage_never_expires_an_order_blindly(
    client: TestClient, db: Session, app: FastAPI, settings: Settings
) -> None:
    body = checkout(client, db)
    _expire(db, body["order"]["reference"])
    gateway = sim(app)
    gateway.fail_requests = True
    report = payments.expire_and_reconcile(db, settings, gateway)
    assert report.errors == 1
    assert get_order(db, body["order"]["reference"]).status == "pending_payment"
    gateway.fail_requests = False


def test_late_capture_after_expiry_confirms_when_stock_remains(
    client: TestClient, db: Session, app: FastAPI, settings: Settings
) -> None:
    body = checkout(client, db)
    _expire(db, body["order"]["reference"])
    payments.expire_and_reconcile(db, settings, sim(app))
    on_hand = level(db, SKU).on_hand
    late = verify(client, body, simulate(client, body))
    assert late.status_code == 200
    assert late.json()["outcome"] == "paid"
    assert late.json()["order"]["status"] == "confirmed"
    assert level(db, SKU).on_hand == on_hand - 1


def test_late_capture_without_stock_goes_to_review(
    client: TestClient, other_client: TestClient, db: Session, app: FastAPI, settings: Settings
) -> None:
    body = checkout(client, db, "ANV-NK-001")  # one of a kind
    _expire(db, body["order"]["reference"])
    payments.expire_and_reconcile(db, settings, sim(app))
    buy(other_client, db, "ANV-NK-001")  # someone else buys the piece meanwhile
    late = verify(client, body, simulate(client, body))
    assert late.status_code == 200
    data = late.json()
    assert data["outcome"] == "review"
    assert data["order"]["status"] == "payment_review"
    assert data["order"]["payment_status"] == "paid"
    assert "refunded" in data["order"]["payment_message"]
    # Internal notes stay internal.
    assert all("refund or fulfil" not in (e["note"] or "") for e in data["order"]["timeline"])
    assert level(db, "ANV-NK-001").on_hand == 0


# ------------------------------------------------------------------ cancellation


def _cancel(client: TestClient, body: dict[str, Any]):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/orders/{body['order']['reference']}/cancel",
        json={"reason": "Changed my mind"},
        headers=token_headers(body),
    )


def test_cancel_unpaid_order_releases_stock(client: TestClient, db: Session) -> None:
    reserved = level(db, SKU).reserved
    body = checkout(client, db)
    response = _cancel(client, body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "cancelled" and data["can_pay"] is False
    assert level(db, SKU).reserved == reserved
    active = db.scalar(
        select(func.count())
        .select_from(InventoryReservation)
        .where(InventoryReservation.status == "active")
    )
    assert active == 0
    assert len(MEMORY_OUTBOX) == 1 and "cancelled" in MEMORY_OUTBOX[0]["Subject"]


def test_cancel_paid_order_restocks_and_requests_refund(client: TestClient, db: Session) -> None:
    body = buy(client, db)
    on_hand = level(db, SKU).on_hand
    data = _cancel(client, body).json()
    assert data["status"] == "cancelled"
    assert data["payment_status"] == "refund_pending"
    assert data["refunds"] == [
        {
            "amount": body["order"]["totals"]["grand_total"],
            "status": "requested",
            "created_at": data["refunds"][0]["created_at"],
        }
    ]
    assert level(db, SKU).on_hand == on_hand + 1
    refund = db.scalar(select(Refund))
    assert refund is not None and refund.amount == Decimal(body["order"]["totals"]["grand_total"])
    # Cancelling twice is refused.
    again = _cancel(client, body)
    assert again.status_code == 409 and again.json()["error"]["code"] == "CANNOT_CANCEL"


def test_cannot_cancel_once_preparation_started(client: TestClient, db: Session) -> None:
    body = buy(client, db)
    db.execute(
        update(Order)
        .where(Order.reference == body["order"]["reference"])
        .values(status="processing")
    )
    db.commit()
    response = _cancel(client, body)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CANNOT_CANCEL"


def test_capture_after_cancellation_goes_to_review(client: TestClient, db: Session) -> None:
    body = checkout(client, db)
    payment = simulate(client, body)  # paid in the pop-up...
    _cancel(client, body)  # ...but the customer cancelled in another tab first
    result = verify(client, body, payment).json()
    assert result["outcome"] == "review"
    assert result["order"]["status"] == "payment_review"


# ------------------------------------------------------------------ Razorpay REST client


def _razorpay(handler: Any) -> RazorpayGateway:
    return RazorpayGateway(
        "rzp_test_key", "test_key_secret", transport=httpx.MockTransport(handler)
    )


def test_razorpay_client_creates_orders_in_paise_with_basic_auth() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "order_RZ1", "amount": 3230100, "currency": "INR"})

    order = _razorpay(handler).create_order(3230100, "ANV-1", {"order_reference": "ANV-1"})
    assert order.id == "order_RZ1"
    assert seen["path"] == "/v1/orders"
    assert seen["body"]["amount"] == 3230100 and seen["body"]["currency"] == "INR"
    assert seen["auth"].startswith("Basic ")


def test_razorpay_signature_uses_order_id_pipe_payment_id() -> None:
    gateway = _razorpay(lambda r: httpx.Response(500))
    good = hmac_sha256("test_key_secret", "order_RZ1|pay_RZ1")
    assert gateway.verify_checkout_signature("order_RZ1", "pay_RZ1", good)
    assert not gateway.verify_checkout_signature("order_RZ2", "pay_RZ1", good)


def test_razorpay_errors_become_friendly_provider_errors() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(PaymentProviderError):
        _razorpay(down).fetch_payment("pay_1")

    def rejected(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"code": "BAD_REQUEST_ERROR"}})

    with pytest.raises(PaymentProviderError) as info:
        _razorpay(rejected).fetch_payment("pay_1")
    assert info.value.details == {"provider_code": "BAD_REQUEST_ERROR"}


def test_full_checkout_against_mocked_razorpay(
    client: TestClient, db: Session, app: FastAPI
) -> None:
    """The real Razorpay code path end to end, with Razorpay's API replaced by a mock."""
    state: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/orders":
            body = json.loads(request.content)
            state["amount"] = body["amount"]
            return httpx.Response(
                200, json={"id": "order_RZ9", "amount": body["amount"], "currency": "INR"}
            )
        if request.url.path == "/v1/payments/pay_RZ9":
            return httpx.Response(
                200,
                json={
                    "id": "pay_RZ9",
                    "order_id": "order_RZ9",
                    "amount": state["amount"],
                    "currency": "INR",
                    "status": "captured",
                    "method": "upi",
                },
            )
        return httpx.Response(404, json={"error": {"code": "BAD_REQUEST_ERROR"}})

    app.state.payment_gateway = _razorpay(handler)
    body = checkout(client, db)
    assert body["payment"]["provider"] == "razorpay"
    assert body["payment"]["key_id"] == "rzp_test_key"
    assert "secret" not in json.dumps(body).lower()
    signature = hmac_sha256("test_key_secret", "order_RZ9|pay_RZ9")
    result = verify(
        client,
        body,
        {
            "provider_order_id": "order_RZ9",
            "provider_payment_id": "pay_RZ9",
            "signature": signature,
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["order"]["status"] == "confirmed"
    attempt = db.scalar(select(PaymentAttempt).execution_options(populate_existing=True))
    assert attempt is not None
    assert (attempt.provider, attempt.status, attempt.method) == ("razorpay", "captured", "upi")


def test_provider_outage_at_checkout_keeps_the_order_and_allows_retry(
    client: TestClient, db: Session, app: FastAPI
) -> None:
    gateway = sim(app)
    gateway.fail_requests = True
    add_to_cart(client, db, SKU)
    response = place_order(client)
    gateway.fail_requests = False
    assert response.status_code == 200
    body = response.json()
    assert body["payment"] is None
    assert "payment provider" in body["payment_error"]
    assert body["order"]["status"] == "pending_payment"
    retry = client.post(
        "/api/v1/payments/retry",
        json={"reference": body["order"]["reference"]},
        headers=token_headers(body),
    )
    assert retry.status_code == 200
    assert retry.json()["payment"]["provider"] == "simulator"
