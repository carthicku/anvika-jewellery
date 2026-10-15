"""Admin operations API: permission matrix, order fulfilment, refunds, payment-review resolution,
inventory adjustments, gold rates, dashboard, customers and the audit log (J9, J10)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import AuditLog, InventoryMovement, Order, Product
from app.services import inventory
from app.services.email import MEMORY_OUTBOX
from tests.api.order_helpers import add_to_cart, buy, level, place_order, variant
from tests.conftest import login_client

SKU = "ANV-RG-002-12"
API = "/api/v1/admin"


@pytest.fixture()
def staff(app: FastAPI, make_user) -> TestClient:  # type: ignore[no-untyped-def]
    make_user(email="staff@example.com", role="staff", full_name="Store Staff")
    with TestClient(app, base_url="http://testserver") as c:
        c.headers["X-CSRF-Token"] = c.get("/api/v1/auth/csrf").json()["csrf_token"]
        yield login_client(c, "staff@example.com")


@pytest.fixture()
def admin(app: FastAPI, make_user) -> TestClient:  # type: ignore[no-untyped-def]
    make_user(email="owner@example.com", role="admin", full_name="Store Owner")
    with TestClient(app, base_url="http://testserver") as c:
        c.headers["X-CSRF-Token"] = c.get("/api/v1/auth/csrf").json()["csrf_token"]
        yield login_client(c, "owner@example.com")


def reference(checkout: dict[str, Any]) -> str:
    ref: str = checkout["order"]["reference"]
    return ref


# ------------------------------------------------------------------ access control


def test_guests_and_customers_cannot_use_admin_endpoints(
    client: TestClient, other_client: TestClient, make_user
) -> None:  # type: ignore[no-untyped-def]
    assert client.get(f"{API}/dashboard").status_code == 401
    make_user(email="cust@example.com")
    login_client(other_client, "cust@example.com")
    for path in ("/dashboard", "/orders", "/inventory", "/customers", "/gold-rates", "/audit-logs"):
        assert other_client.get(f"{API}{path}").status_code == 403, path


def test_staff_permissions_are_limited(staff: TestClient) -> None:
    for path in ("/dashboard", "/orders", "/inventory", "/inventory/movements", "/customers"):
        assert staff.get(f"{API}{path}").status_code == 200, path
    # Money and pricing powers are admin-only.
    assert staff.get(f"{API}/gold-rates").status_code == 403
    assert staff.get(f"{API}/audit-logs").status_code == 403
    response = staff.post(f"{API}/gold-rates/preview", json={"purity": "22K", "rate_per_gram": "1"})
    assert response.status_code == 403


# ------------------------------------------------------------------ fulfilment


def test_fulfil_a_paid_order_end_to_end(
    client: TestClient, staff: TestClient, admin: TestClient, db: Session
) -> None:
    checkout = buy(client, db)
    ref = reference(checkout)
    MEMORY_OUTBOX.clear()

    listing = staff.get(f"{API}/orders", params={"status": "confirmed", "q": ref}).json()
    assert [o["reference"] for o in listing["items"]] == [ref]
    detail = staff.get(f"{API}/orders/{ref}").json()
    assert "start_processing" in detail["allowed_actions"]
    assert detail["payment_attempts"][0]["status"] == "captured"

    # Can't skip a step.
    ship = {"carrier": "Sample Courier", "tracking_number": "TRK123456", "tracking_url": None}
    early = staff.post(f"{API}/orders/{ref}/shipments", json=ship)
    assert early.status_code == 409 and early.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    assert (
        staff.post(f"{API}/orders/{ref}/status", json={"action": "start_processing"}).json()[
            "order"
        ]["status"]
        == "processing"
    )
    shipped = staff.post(
        f"{API}/orders/{ref}/shipments",
        json={**ship, "tracking_url": "https://track.example.com/TRK123456"},
    )
    assert shipped.status_code == 200, shipped.text
    assert shipped.json()["order"]["status"] == "shipped"
    assert any("on its way" in m["Subject"] for m in MEMORY_OUTBOX)

    delivered = staff.post(f"{API}/orders/{ref}/status", json={"action": "mark_delivered"}).json()
    assert delivered["order"]["status"] == "delivered"
    assert delivered["order"]["shipments"][0]["status"] == "delivered"

    # The customer sees the progress (but not internal notes).
    staff.post(f"{API}/orders/{ref}/notes", json={"note": "Packed by Priya"})
    mine = client.get(
        f"/api/v1/orders/{ref}", headers={"X-Order-Access-Token": checkout["access_token"]}
    ).json()
    kinds = [e["kind"] for e in mine["timeline"]]
    assert kinds[-2:] == ["shipped", "delivered"]
    assert all("Priya" not in (e["note"] or "") for e in mine["timeline"])

    actions = [
        log["action"]
        for log in admin.get(f"{API}/audit-logs", params={"entity_id": ref}).json()["items"]
    ]
    assert {"order.processing", "order.shipped", "order.delivered", "order.note"} <= set(actions)


def test_unpaid_orders_cannot_be_fulfilled(
    client: TestClient, staff: TestClient, db: Session
) -> None:
    add_to_cart(client, db, SKU)
    ref = reference(place_order(client).json())
    response = staff.post(f"{API}/orders/{ref}/status", json={"action": "start_processing"})
    assert response.status_code == 409


def test_tracking_link_must_be_https(client: TestClient, staff: TestClient, db: Session) -> None:
    ref = reference(buy(client, db))
    staff.post(f"{API}/orders/{ref}/status", json={"action": "start_processing"})
    response = staff.post(
        f"{API}/orders/{ref}/shipments",
        json={"carrier": "X", "tracking_number": "T1234", "tracking_url": "javascript:alert(1)"},
    )
    assert response.status_code == 422


# ------------------------------------------------------------------ cancellation and refunds


def test_partial_refund_is_requested_then_sent_to_the_provider(
    client: TestClient, staff: TestClient, admin: TestClient, db: Session
) -> None:
    ref = reference(buy(client, db))
    assert (
        staff.post(f"{API}/orders/{ref}/refunds", json={"amount": "1000.00", "reason": "Goodwill"})
    ).status_code == 403

    too_much = admin.post(
        f"{API}/orders/{ref}/refunds", json={"amount": "99999999.00", "reason": "Oops"}
    )
    assert too_much.status_code == 422

    requested = admin.post(
        f"{API}/orders/{ref}/refunds", json={"amount": "1000.00", "reason": "Goodwill"}
    ).json()
    assert requested["order"]["payment_status"] == "refund_pending"
    refund = requested["refunds"][0]
    assert refund["status"] == "requested" and "execute_refund" in requested["allowed_actions"]

    MEMORY_OUTBOX.clear()
    sent = admin.post(f"{API}/orders/{ref}/refunds/{refund['id']}/execute")
    assert sent.status_code == 200, sent.text
    body = sent.json()
    assert body["refunds"][0]["status"] == "processed"
    assert body["refunds"][0]["provider_refund_id"].startswith("rfnd_sim_")
    assert body["order"]["payment_status"] == "partially_refunded"
    assert Decimal(body["refundable"]) == Decimal(body["order"]["totals"]["grand_total"]) - 1000
    assert any("refund" in m["Subject"].lower() for m in MEMORY_OUTBOX)
    # Sending the same refund twice is refused.
    again = admin.post(f"{API}/orders/{ref}/refunds/{refund['id']}/execute")
    assert again.status_code == 409


def test_admin_cancels_paid_order_with_full_refund(
    client: TestClient, admin: TestClient, db: Session
) -> None:
    on_hand = level(db, SKU).on_hand
    ref = reference(buy(client, db))
    assert level(db, SKU).on_hand == on_hand - 1
    no_reason = admin.post(f"{API}/orders/{ref}/cancel", json={"reason": ""})
    assert no_reason.status_code == 422
    cancelled = admin.post(f"{API}/orders/{ref}/cancel", json={"reason": "Customer called"}).json()
    assert cancelled["order"]["status"] == "cancelled"
    assert level(db, SKU).on_hand == on_hand
    refund = cancelled["refunds"][0]
    done = admin.post(f"{API}/orders/{ref}/refunds/{refund['id']}/execute").json()
    assert done["order"]["payment_status"] == "refunded"
    assert Decimal(done["refundable"]) == 0


def _make_review_case(client: TestClient, db: Session, sku: str = SKU) -> str:
    """A paid order that the system could not confirm (as after a late capture with no stock)."""
    add_to_cart(client, db, sku)
    body = place_order(client).json()
    ref = reference(body)
    order = db.scalar(select(Order).where(Order.reference == ref))
    assert order is not None
    inventory.release(db, order.id, note="test setup")
    db.execute(
        update(Order)
        .where(Order.id == order.id)
        .values(status="payment_review", payment_status="paid", paid_at=utcnow())
    )
    db.commit()
    return ref


def test_review_can_be_confirmed_when_stock_allows(
    client: TestClient, admin: TestClient, staff: TestClient, db: Session
) -> None:
    ref = _make_review_case(client, db)
    on_hand = level(db, SKU).on_hand
    assert staff.post(f"{API}/orders/{ref}/review", json={"decision": "confirm"}).status_code == 403
    result = admin.post(f"{API}/orders/{ref}/review", json={"decision": "confirm"}).json()
    assert result["order"]["status"] == "confirmed"
    assert level(db, SKU).on_hand == on_hand - 1


def test_review_can_be_refunded(client: TestClient, admin: TestClient, db: Session) -> None:
    ref = _make_review_case(client, db)
    result = admin.post(
        f"{API}/orders/{ref}/review", json={"decision": "refund", "note": "Sold out"}
    ).json()
    assert result["order"]["status"] == "cancelled"
    assert result["order"]["payment_status"] == "refund_pending"
    assert result["refunds"][0]["status"] == "requested"


# ------------------------------------------------------------------ inventory


def test_stock_adjustments_are_ledgered_and_audited(
    staff: TestClient, admin: TestClient, db: Session
) -> None:
    vid = str(variant(db, SKU).id)
    on_hand = level(db, SKU).on_hand
    rows = staff.get(f"{API}/inventory", params={"q": SKU}).json()["items"]
    assert [r["sku"] for r in rows] == [SKU]

    added = staff.post(
        f"{API}/inventory/{vid}/adjust", json={"delta": 5, "note": "New stock from workshop"}
    )
    assert added.status_code == 200, added.text
    assert added.json()["on_hand"] == on_hand + 5

    assert (
        staff.post(f"{API}/inventory/{vid}/adjust", json={"delta": 0, "note": "x"}).status_code
        == 422
    )
    assert (
        staff.post(f"{API}/inventory/{vid}/adjust", json={"delta": -1, "note": ""}).status_code
        == 422
    )

    movements = staff.get(f"{API}/inventory/movements", params={"variant_id": vid}).json()["items"]
    latest = movements[0]
    assert (latest["reason"], latest["delta_on_hand"], latest["actor_email"]) == (
        "adjustment",
        5,
        "staff@example.com",
    )
    log = admin.get(f"{API}/audit-logs", params={"action": "inventory.adjust"}).json()["items"][0]
    assert log["entity_id"] == SKU and log["changes"]["delta"] == 5


def test_stock_cannot_drop_below_reserved(
    client: TestClient, staff: TestClient, db: Session
) -> None:
    add_to_cart(client, db, "ANV-NK-001")  # one in stock
    place_order(client)  # reserves it
    vid = str(variant(db, "ANV-NK-001").id)
    response = staff.post(f"{API}/inventory/{vid}/adjust", json={"delta": -1, "note": "Damaged"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ADJUSTMENT_BELOW_RESERVED"
    assert level(db, "ANV-NK-001").on_hand == 1


def test_low_stock_filter_and_threshold(staff: TestClient, db: Session) -> None:
    vid = str(variant(db, SKU).id)
    response = staff.put(f"{API}/inventory/{vid}/threshold", json={"low_stock_threshold": 50})
    assert response.json()["stock_status"] == "low_stock"
    low = staff.get(f"{API}/inventory", params={"low_only": True, "q": SKU}).json()["items"]
    assert [r["sku"] for r in low] == [SKU]


# ------------------------------------------------------------------ gold rates


def test_gold_rate_preview_shows_every_affected_price(admin: TestClient) -> None:
    preview = admin.post(
        f"{API}/gold-rates/preview", json={"purity": "22K", "rate_per_gram": "7500.00"}
    ).json()
    assert preview["current_rate"] == "7150.00"
    assert preview["change_percent"] == "4.90"
    assert preview["needs_confirmation"] is False
    band = next(i for i in preview["impacts"] if i["sku"] == SKU)
    assert band["old_price"] == "27402.74"
    assert Decimal(band["new_price"]) > Decimal(band["old_price"])


def test_large_rate_change_needs_confirmation_and_is_audited(
    admin: TestClient, db: Session
) -> None:
    body = {"purity": "22K", "rate_per_gram": "9000.00", "source_note": "Test source 15-Oct"}
    refused = admin.post(f"{API}/gold-rates", json=body)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "LARGE_RATE_CHANGE"

    product = db.scalar(select(Product).where(Product.slug == "everyday-gold-band"))
    assert product is not None
    before = product.price_from
    created = admin.post(f"{API}/gold-rates", json={**body, "confirm_large_change": True})
    assert created.status_code == 201, created.text
    db.refresh(product)
    assert product.price_from is not None and before is not None and product.price_from > before

    rates = admin.get(f"{API}/gold-rates").json()
    current = next(r for r in rates["current"] if r["purity"] == "22K")
    assert current["rate_per_gram"] == "9000.00" and current["stale"] is False
    assert rates["history"][0]["source_note"] == "Test source 15-Oct"
    log = db.scalar(select(AuditLog).where(AuditLog.action == "gold_rate.create"))
    assert log is not None and log.changes["confirmed_large_change"] is True
    assert log.changes["previous"] == "7150.00"


def test_rate_requires_a_source_note(admin: TestClient) -> None:
    response = admin.post(
        f"{API}/gold-rates", json={"purity": "22K", "rate_per_gram": "7200.00", "source_note": ""}
    )
    assert response.status_code == 422


# ------------------------------------------------------------------ dashboard, customers


def test_dashboard_counts_only_paid_money(
    client: TestClient, other_client: TestClient, staff: TestClient, db: Session
) -> None:
    before = staff.get(f"{API}/dashboard").json()
    paid = buy(client, db)
    add_to_cart(other_client, db, "ANV-PD-001")
    place_order(other_client)  # unpaid: must not count as revenue
    after = staff.get(f"{API}/dashboard").json()
    assert after["paid_orders"] == before["paid_orders"] + 1
    assert Decimal(after["paid_revenue"]) - Decimal(before["paid_revenue"]) == Decimal(
        paid["order"]["totals"]["grand_total"]
    )
    assert after["pending_payment"] == before["pending_payment"] + 1
    assert after["to_fulfil"] == before["to_fulfil"] + 1
    assert any(b["product_slug"] == "everyday-gold-band" for b in after["best_sellers"])
    assert {r["purity"] for r in after["gold_rates"]} == {"24K", "22K", "18K", "14K"}
    assert all(set(r) >= {"stale", "age_hours"} for r in after["gold_rates"])


def test_customer_list_and_detail(
    client: TestClient, staff: TestClient, db: Session, make_user
) -> None:  # type: ignore[no-untyped-def]
    make_user(email="meera@example.com", full_name="Meera Iyer")
    login_client(client, "meera@example.com")
    add_to_cart(client, db, SKU)
    place_order(client, email=None)
    found = staff.get(f"{API}/customers", params={"q": "meera"}).json()["items"]
    assert [c["email"] for c in found] == ["meera@example.com"]
    assert found[0]["order_count"] == 1 and found[0]["paid_total"] == "0.00"
    detail = staff.get(f"{API}/customers/{found[0]['id']}").json()
    assert detail["customer"]["full_name"] == "Meera Iyer"
    assert len(detail["orders"]) == 1
    # Staff accounts are not "customers".
    assert staff.get(f"{API}/customers", params={"q": "staff@"}).json()["items"] == []


def test_movements_record_sales_with_order_reference(
    client: TestClient, staff: TestClient, db: Session
) -> None:
    ref = reference(buy(client, db))
    vid = str(variant(db, SKU).id)
    items = staff.get(f"{API}/inventory/movements", params={"variant_id": vid}).json()["items"]
    sale = next(m for m in items if m["reason"] == "sale")
    assert sale["order_reference"] == ref and sale["delta_on_hand"] == -1
    assert db.scalar(select(InventoryMovement).where(InventoryMovement.reason == "sale"))
