"""Returns/exchanges and verified-purchase reviews (Phase 7 after-sales)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import AuditLog, InventoryMovement, Order, OrderEvent, OrderItem, Product
from app.services.email import MEMORY_OUTBOX
from tests.api.order_helpers import add_to_cart, buy, level, place_order, token_headers, variant
from tests.conftest import login_client

SKU = "ANV-RG-002-12"
API = "/api/v1/admin"
REASON = "The ring is too small for me, sorry."


def deliver(staff: TestClient, ref: str) -> None:
    assert staff.post(f"{API}/orders/{ref}/status", json={"action": "start_processing"}).is_success
    shipped = staff.post(
        f"{API}/orders/{ref}/shipments",
        json={"carrier": "Sample Courier", "tracking_number": "TRK123456", "tracking_url": None},
    )
    assert shipped.is_success, shipped.text
    assert staff.post(f"{API}/orders/{ref}/status", json={"action": "mark_delivered"}).is_success


def delivered_order(client: TestClient, staff: TestClient, db: Session, quantity: int = 1):  # type: ignore[no-untyped-def]
    checkout = buy(client, db, SKU, quantity)
    ref: str = checkout["order"]["reference"]
    deliver(staff, ref)
    return ref, token_headers(checkout)


def ask(
    client: TestClient,
    ref: str,
    headers: dict[str, str],
    kind: str = "return",
    items: list[dict[str, int]] | None = None,
    reason: str = REASON,
):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/orders/{ref}/returns",
        json={"kind": kind, "reason": reason, "items": items or [{"position": 0, "quantity": 1}]},
        headers=headers,
    )


# ------------------------------------------------------------------ returns


def test_return_for_refund_end_to_end(
    client: TestClient, staff: TestClient, admin: TestClient, db: Session
) -> None:
    ref, headers = delivered_order(client, staff, db)
    order = client.get(f"/api/v1/orders/{ref}", headers=headers).json()
    assert order["returnable_items"] == [
        {
            "position": 0,
            "product_name": order["items"][0]["product_name"],
            "variant_label": order["items"][0]["variant_label"],
            "quantity": 1,
            "kinds": ["return", "exchange"],
            "deadline": order["returnable_items"][0]["deadline"],
        }
    ]
    MEMORY_OUTBOX.clear()
    created = ask(client, ref, headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["returns"][0]["status"] == "requested"
    assert body["returnable_items"] == []
    assert body["timeline"][-1]["kind"] == "return_requested"
    assert any("request for order" in m["Subject"] for m in MEMORY_OUTBOX)

    again = ask(client, ref, headers)
    assert again.status_code == 409 and again.json()["error"]["code"] == "RETURN_ALREADY_OPEN"

    rows = staff.get(f"{API}/returns", params={"status": "requested"}).json()["items"]
    assert [r["order_reference"] for r in rows] == [ref]
    return_id = rows[0]["id"]
    detail = staff.get(f"{API}/returns/{return_id}").json()
    assert detail["allowed_actions"] == ["approve", "reject"]
    assert detail["suggested_refund"] == order["items"][0]["line_total"]

    # Can't skip ahead.
    early = staff.post(f"{API}/returns/{return_id}/receive", json={"restock_positions": [0]})
    assert early.status_code == 409 and early.json()["error"]["code"] == "INVALID_RETURN_STATE"

    approved = staff.post(f"{API}/returns/{return_id}/approve", json={"note": "Use any courier."})
    assert approved.json()["status"] == "approved"

    on_hand = level(db, SKU).on_hand
    received = staff.post(
        f"{API}/returns/{return_id}/receive", json={"restock_positions": [0], "note": ""}
    ).json()
    assert received["status"] == "received" and received["items"][0]["restock"] is True
    assert level(db, SKU).on_hand == on_hand + 1
    movement = db.scalars(
        select(InventoryMovement)
        .where(InventoryMovement.reason == "return_restock")
        .order_by(InventoryMovement.created_at.desc())
    ).first()
    assert movement is not None and movement.delta_on_hand == 1
    assert db.scalar(select(Order.status).where(Order.reference == ref)) == "returned"

    # Money is an admin power.
    refund_in = {"amount": detail["suggested_refund"], "note": ""}
    assert staff.post(f"{API}/returns/{return_id}/refund", json=refund_in).status_code == 403
    refunded = admin.post(f"{API}/returns/{return_id}/refund", json=refund_in).json()
    assert refunded["status"] == "refunded" and refunded["refund_status"] == "requested"

    # The refund is sent like any other order refund.
    sent = admin.post(f"{API}/orders/{ref}/refunds/{refunded['refund_id']}/execute").json()
    # Shipping is not part of the suggested amount, so the order is partly refunded.
    assert sent["order"]["payment_status"] == "partially_refunded"

    mine = client.get(f"/api/v1/orders/{ref}", headers=headers).json()
    assert mine["status"] == "returned" and mine["returns"][0]["status"] == "refunded"
    assert mine["returns"][0]["store_note"] == "Use any courier."
    actions = set(db.scalars(select(AuditLog.action).where(AuditLog.entity_id == return_id)))
    assert {"return.approve", "return.receive", "return.refund"} <= actions


def test_return_rules(
    client: TestClient, other_client: TestClient, staff: TestClient, db: Session
) -> None:
    # Not delivered yet.
    checkout = buy(client, db, SKU, 2)
    ref = checkout["order"]["reference"]
    headers = token_headers(checkout)
    early = ask(client, ref, headers)
    assert early.status_code == 409 and early.json()["error"]["code"] == "NOT_DELIVERED"

    deliver(staff, ref)
    # Someone else's order is invisible.
    assert ask(other_client, ref, {}).status_code == 404
    # More than was bought.
    too_many = ask(client, ref, headers, items=[{"position": 0, "quantity": 3}])
    assert too_many.status_code == 422
    # An item that wasn't eligible for returns when it was bought (exchange only).
    order_id = db.scalar(select(Order.id).where(Order.reference == ref))
    item = db.scalar(select(OrderItem).where(OrderItem.order_id == order_id))
    assert item is not None
    item.price_inputs = {**item.price_inputs, "return_eligible": False}
    db.commit()
    refused = ask(client, ref, headers)
    assert refused.status_code == 422
    assert ask(client, ref, headers, kind="exchange").status_code == 201

    # A partial request leaves the rest returnable once it is closed... but not after the window.
    db.execute(
        update(OrderEvent)
        .where(OrderEvent.order_id == order_id, OrderEvent.kind == "delivered")
        .values(created_at=utcnow() - timedelta(days=16))
    )
    db.commit()
    rows = staff.get(f"{API}/returns").json()["items"]
    staff.post(f"{API}/returns/{rows[0]['id']}/reject", json={"note": "Outside our policy."})
    late = client.get(f"/api/v1/orders/{ref}", headers=headers).json()
    assert late["returnable_items"] == []
    assert ask(client, ref, headers, kind="exchange").json()["error"]["code"] == (
        "RETURN_NOT_AVAILABLE"
    )


def test_reject_needs_a_reason_and_allows_a_new_request(
    client: TestClient, staff: TestClient, db: Session
) -> None:
    ref, headers = delivered_order(client, staff, db)
    assert ask(client, ref, headers).status_code == 201
    return_id = staff.get(f"{API}/returns").json()["items"][0]["id"]
    assert staff.post(f"{API}/returns/{return_id}/reject", json={"note": ""}).status_code == 422
    rejected = staff.post(
        f"{API}/returns/{return_id}/reject", json={"note": "The piece has been resized."}
    ).json()
    assert rejected["status"] == "rejected" and rejected["allowed_actions"] == []
    mine = client.get(f"/api/v1/orders/{ref}", headers=headers).json()
    assert mine["returns"][0]["store_note"] == "The piece has been resized."
    assert mine["returnable_items"][0]["quantity"] == 1  # rejected lines can be asked for again


def test_exchange_is_closed_without_refund_or_restock(
    client: TestClient, staff: TestClient, admin: TestClient, db: Session
) -> None:
    ref, headers = delivered_order(client, staff, db)
    assert ask(client, ref, headers, kind="exchange").status_code == 201
    return_id = staff.get(f"{API}/returns").json()["items"][0]["id"]
    staff.post(f"{API}/returns/{return_id}/approve", json={"note": ""})
    on_hand = level(db, SKU).on_hand
    received = staff.post(f"{API}/returns/{return_id}/receive", json={}).json()
    assert received["items"][0]["restock"] is False
    assert level(db, SKU).on_hand == on_hand
    assert received["allowed_actions"] == ["close"]
    refund = admin.post(f"{API}/returns/{return_id}/refund", json={"amount": "1.00"})
    assert refund.status_code == 409
    assert staff.post(f"{API}/returns/{return_id}/close", json={"note": ""}).status_code == 422
    closed = staff.post(f"{API}/returns/{return_id}/close", json={"note": "Size 14 sent out."})
    assert closed.json()["status"] == "closed"
    assert db.scalar(select(Order.status).where(Order.reference == ref)) == "delivered"


def test_customers_cannot_use_return_admin(other_client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user(email="cust@example.com")
    login_client(other_client, "cust@example.com")
    assert other_client.get(f"{API}/returns").status_code == 403
    assert other_client.get(f"{API}/reviews").status_code == 403


# ------------------------------------------------------------------ reviews


def slug(db: Session) -> str:
    product = db.get(Product, variant(db, SKU).product_id)
    assert product is not None
    return product.slug


REVIEW = {"rating": 5, "title": "Lovely ring", "body": "Beautiful finish and it fits perfectly."}


def test_only_delivered_buyers_can_review_and_staff_approve_first(
    client: TestClient, staff: TestClient, make_user, db: Session
) -> None:  # type: ignore[no-untyped-def]
    path = f"/api/v1/products/{slug(db)}/reviews"
    response = client.get(path)
    assert response.headers["Cache-Control"] == "no-cache"  # publishing shows up at once
    public = response.json()
    assert public["summary"] == {"count": 0, "average": None}
    assert public["reviews"]["items"] == []
    assert client.get(f"{path}/mine").status_code == 401

    make_user(email="asha@example.com", full_name="Asha Rao")
    login_client(client, "asha@example.com")
    assert client.get(f"{path}/mine").json() == {"can_review": False, "review": None}
    denied = client.put(f"{path}/mine", json=REVIEW)
    assert denied.status_code == 403 and denied.json()["error"]["code"] == (
        "NOT_A_VERIFIED_PURCHASE"
    )

    # Bought but not delivered yet: still no.
    add_to_cart(client, db, SKU)
    checkout = place_order(client).json()
    from tests.api.order_helpers import simulate, verify

    assert verify(client, checkout, simulate(client, checkout)).json()["outcome"] == "paid"
    assert client.put(f"{path}/mine", json=REVIEW).status_code == 403
    deliver(staff, checkout["order"]["reference"])

    saved = client.put(f"{path}/mine", json=REVIEW)
    assert saved.status_code == 200, saved.text
    assert saved.json()["review"]["status"] == "pending"
    assert client.get(path).json()["summary"]["count"] == 0  # not public until approved

    pending = staff.get(f"{API}/reviews", params={"status": "pending"}).json()["items"]
    assert len(pending) == 1 and pending[0]["verified_purchase"] is True
    approved = staff.post(
        f"{API}/reviews/{pending[0]['id']}/moderate", json={"decision": "approve"}
    )
    assert approved.json()["status"] == "approved"
    public = client.get(path).json()
    assert public["summary"] == {"count": 1, "average": "5.0"}
    shown = public["reviews"]["items"][0]
    assert shown["author_name"] == "Asha R." and shown["verified_purchase"] is True
    assert "email" not in shown

    # Editing sends it back to moderation and hides it.
    edited = client.put(f"{path}/mine", json={**REVIEW, "rating": 3}).json()
    assert edited["review"]["status"] == "pending"
    assert client.get(path).json()["summary"]["count"] == 0
    rejected = staff.post(
        f"{API}/reviews/{pending[0]['id']}/moderate",
        json={"decision": "reject", "note": "Mentions another customer."},
    ).json()
    assert rejected["status"] == "rejected"
    assert client.get(f"{path}/mine").json()["review"]["status_label"] == "Not published"
    logs = db.scalars(select(AuditLog.action).where(AuditLog.entity_type == "product_review"))
    assert {"review.approved", "review.rejected"} <= set(logs)


def test_review_validation(client: TestClient, db: Session) -> None:
    path = f"/api/v1/products/{slug(db)}/reviews/mine"
    body: dict[str, Any] = {**REVIEW, "rating": 6}
    assert client.put(path, json=body).status_code in (401, 422)
    assert client.get("/api/v1/products/no-such-piece/reviews").status_code == 404
