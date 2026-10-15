"""Checkout API: quote, idempotent order creation, expected-total consent, stock reservation,
coupon limits, snapshots and access control (journeys J3, J4, J11)."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import (
    Cart,
    CouponRedemption,
    GoldRate,
    InventoryReservation,
    Order,
    OrderItem,
    PaymentAttempt,
    ShippingZone,
)
from app.services import store_settings
from tests.api.order_helpers import (
    ADDRESS,
    add_to_cart,
    buy,
    level,
    new_key,
    place_order,
    quote,
    token_headers,
)
from tests.conftest import login_client

SKU = "ANV-RG-002-12"  # Everyday Gold Band, size 12 (8 in stock)


def order_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Order)) or 0


# ------------------------------------------------------------------ quote


def test_quote_prices_delivery_options_without_side_effects(
    client: TestClient, db: Session
) -> None:
    add_to_cart(client, db, SKU)
    before = level(db, SKU).reserved
    body = quote(client, method="express")
    assert body["serviceable"] is True
    assert [o["code"] for o in body["shipping_options"]] == ["standard", "express"]
    assert body["shipping_method"] == "express"
    totals = body["cart"]["totals"]
    assert totals["shipping_label"] == "Express delivery"
    assert totals["shipping_fee"] == "499.00"  # express has no free-delivery threshold
    assert Decimal(totals["grand_total"]) % 1 == 0
    assert body["cart"]["can_checkout"] is True
    assert order_count(db) == 0
    assert level(db, SKU).reserved == before


def test_quote_for_unserviceable_pincode_blocks_checkout(client: TestClient, db: Session) -> None:
    db.add(ShippingZone(name="Bengaluru only", pincode_prefixes=["560"], extra_days=0))
    db.commit()
    add_to_cart(client, db, SKU)
    body = quote(client, pincode="110001")
    assert body["serviceable"] is False
    assert body["shipping_options"] == []
    assert body["cart"]["can_checkout"] is False
    response = place_order(client, address={**ADDRESS, "pincode": "110001"}, expected_total="1.00")
    assert response.status_code == 422
    assert "shipping_address.pincode" in response.json()["error"]["details"]["fields"]


def test_quote_rejects_malformed_pincode(client: TestClient) -> None:
    response = client.post("/api/v1/checkout/quote", json={"pincode": "012345"})
    assert response.status_code == 422


# ------------------------------------------------------------------ order creation


def test_guest_order_reserves_stock_and_opens_a_payment(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU, 2)
    stock = level(db, SKU)
    on_hand, reserved = stock.on_hand, stock.reserved
    expected = quote(client)["cart"]["totals"]["grand_total"]

    response = place_order(client, expected_total=expected, customer_note="Gift wrap please")
    assert response.status_code == 200, response.text
    body = response.json()
    order = body["order"]
    assert order["status"] == "pending_payment"
    assert order["payment_status"] == "unpaid"
    assert order["totals"]["grand_total"] == expected
    assert order["email"] == "guest@example.com"
    assert order["reference"].startswith("ANV-")
    assert order["can_pay"] is True and order["can_cancel"] is True
    assert order["items"][0]["quantity"] == 2 and order["items"][0]["sku"] == SKU
    assert order["customer_note"] == "Gift wrap please"
    assert [e["kind"] for e in order["timeline"]] == ["order_created"]
    # Guests get a private access token; the amount is the backend's total in paise.
    assert body["access_token"] and len(body["access_token"]) >= 40
    payment = body["payment"]
    assert payment["provider"] == "simulator"
    assert payment["amount_paise"] == int(Decimal(expected) * 100)
    assert payment["prefill"] == {
        "name": "Asha Rao",
        "email": "guest@example.com",
        "contact": "+919876543210",
    }
    assert body["payment_error"] is None
    # Stock is held (not sold) and the cart stays until payment succeeds.
    stock = level(db, SKU)
    assert (stock.on_hand, stock.reserved) == (on_hand, reserved + 2)
    assert db.scalar(select(Cart.status).where(Cart.id == db.scalar(select(Order.cart_id)))) == (
        "active"
    )


def test_same_idempotency_key_returns_the_same_order(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU)
    key = new_key()
    first = place_order(client, key=key).json()
    second = place_order(client, key=key)
    assert second.status_code == 200
    assert second.json()["order"]["reference"] == first["order"]["reference"]
    assert second.json()["payment"]["provider_order_id"] == first["payment"]["provider_order_id"]
    assert second.json()["access_token"] == first["access_token"]
    assert order_count(db) == 1
    assert db.scalar(select(func.count()).select_from(PaymentAttempt)) == 1
    assert db.scalar(select(func.count()).select_from(InventoryReservation)) == 1


def test_idempotency_key_cannot_be_replayed_by_another_cart(
    client: TestClient, other_client: TestClient, db: Session
) -> None:
    add_to_cart(client, db, SKU)
    key = new_key()
    assert place_order(client, key=key).status_code == 200
    add_to_cart(other_client, db, SKU)
    response = place_order(other_client, key=key)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_unchanged_cart_reuses_the_pending_order(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU)
    reserved = level(db, SKU).reserved
    first = place_order(client).json()
    again = place_order(client).json()  # new key, e.g. the page was reloaded
    assert again["order"]["reference"] == first["order"]["reference"]
    assert order_count(db) == 1
    assert level(db, SKU).reserved == reserved + 1


def test_changed_cart_replaces_the_pending_order_and_releases_its_stock(
    client: TestClient, db: Session
) -> None:
    add_to_cart(client, db, SKU)
    reserved_before = level(db, SKU).reserved
    first = place_order(client).json()
    assert level(db, SKU).reserved == reserved_before + 1
    add_to_cart(client, db, SKU)  # now 2
    second = place_order(client).json()
    assert second["order"]["reference"] != first["order"]["reference"]
    old = db.scalar(
        select(Order)
        .where(Order.reference == first["order"]["reference"])
        .execution_options(populate_existing=True)
    )
    assert old is not None and old.status == "expired"
    assert old.pricing_context["superseded"] is True
    assert level(db, SKU).reserved == reserved_before + 2


def test_total_mismatch_is_refused_with_the_new_total(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU)
    reserved = level(db, SKU).reserved
    real = quote(client)["cart"]["totals"]["grand_total"]
    response = place_order(client, expected_total="1.00")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "PRICE_CHANGED"
    assert error["details"]["grand_total"] == real
    assert order_count(db) == 0
    assert level(db, SKU).reserved == reserved


def test_browser_cannot_send_prices(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU)
    response = place_order(client, grand_total="1.00")
    assert response.status_code == 422
    assert order_count(db) == 0


def test_terms_email_and_idempotency_key_are_required(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU)
    response = place_order(client, terms_accepted=False)
    assert response.status_code == 422
    assert "terms_accepted" in response.json()["error"]["details"]["fields"]
    response = place_order(client, email=None)
    assert response.status_code == 422
    assert "email" in response.json()["error"]["details"]["fields"]
    response = client.post(
        "/api/v1/checkout/orders",
        json={
            "email": "guest@example.com",
            "shipping_address": ADDRESS,
            "shipping_method": "standard",
            "expected_total": "1.00",
            "terms_accepted": True,
        },
    )
    assert response.status_code == 422
    assert order_count(db) == 0


def test_empty_cart_cannot_check_out(client: TestClient) -> None:
    response = place_order(client, expected_total="1.00")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CART_EMPTY"


def test_invalid_address_is_rejected(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU)
    bad = {**ADDRESS, "state": "Atlantis", "phone": "12345"}
    response = place_order(client, address=bad, expected_total="1.00")
    assert response.status_code == 422
    details = response.json()["error"]["details"]["fields"]
    assert any("state" in key for key in details) and any("phone" in key for key in details)


def test_last_piece_goes_to_the_first_buyer(
    client: TestClient, other_client: TestClient, db: Session
) -> None:
    add_to_cart(client, db, "ANV-NK-001")  # one of a kind
    add_to_cart(other_client, db, "ANV-NK-001")
    assert place_order(client).status_code == 200
    response = place_order(other_client, expected_total="1.00")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "CART_NOT_READY"
    assert any("out of stock" in issue for issue in error["details"]["blocking_issues"])
    assert level(db, "ANV-NK-001").reserved == 1


def test_price_increase_must_be_accepted_before_checkout(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU)
    db.add(
        GoldRate(
            purity="22K", rate_per_gram=Decimal("8000.00"), effective_from=utcnow(), source_note="t"
        )
    )
    db.commit()
    response = place_order(client, expected_total="1.00")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CART_NOT_READY"
    assert client.post("/api/v1/cart/accept-prices").status_code == 200
    assert place_order(client).status_code == 200


def test_stale_gold_rate_blocks_checkout_only_when_enabled(client: TestClient, db: Session) -> None:
    add_to_cart(client, db, SKU)
    store_settings.set_group(
        db,
        "pricing_policy",
        {"block_checkout_when_rate_stale": True, "gold_rate_stale_after_hours": 0},
    )
    db.commit()
    cart = client.get("/api/v1/cart").json()
    assert cart["can_checkout"] is False
    assert any("being updated" in issue for issue in cart["blocking_issues"])
    assert place_order(client, expected_total="1.00").json()["error"]["code"] == "CART_NOT_READY"
    store_settings.set_group(db, "pricing_policy", {"block_checkout_when_rate_stale": False})
    db.commit()
    assert place_order(client).status_code == 200


def test_order_snapshot_does_not_change_when_gold_rate_changes(
    client: TestClient, db: Session
) -> None:
    add_to_cart(client, db, SKU)
    body = place_order(client).json()
    reference = body["order"]["reference"]
    before = client.get(f"/api/v1/orders/{reference}", headers=token_headers(body)).json()
    db.add(
        GoldRate(
            purity="22K", rate_per_gram=Decimal("9000.00"), effective_from=utcnow(), source_note="t"
        )
    )
    db.commit()
    after = client.get(f"/api/v1/orders/{reference}", headers=token_headers(body)).json()
    assert after["totals"] == before["totals"]
    assert after["items"] == before["items"]
    item = db.scalar(select(OrderItem))
    assert item is not None
    assert item.price_inputs["gold_rate_per_gram"] == "7150.00"
    assert item.price_inputs["purity"] == "22K"


# ------------------------------------------------------------------ coupons


def test_coupon_is_reserved_then_limited_per_guest_email(
    client: TestClient, other_client: TestClient, db: Session
) -> None:
    add_to_cart(client, db, SKU)
    assert client.post("/api/v1/cart/coupon", json={"code": "WELCOME5"}).status_code == 200
    body = place_order(client).json()
    assert Decimal(body["order"]["totals"]["coupon_discount"]) > 0
    assert body["order"]["coupon_code"] == "WELCOME5"
    redemption = db.scalar(select(CouponRedemption))
    assert redemption is not None and redemption.status == "reserved"

    # Same guest email in another browser: one use per customer.
    add_to_cart(other_client, db, SKU)
    assert other_client.post("/api/v1/cart/coupon", json={"code": "WELCOME5"}).status_code == 200
    response = place_order(other_client, email="GUEST@example.com")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "COUPON_USAGE_LIMIT"
    # A different email may use it.
    assert place_order(other_client, email="someone@example.com").status_code == 200


# ------------------------------------------------------------------ access


def test_signed_in_order_uses_account_email_and_is_private(
    client: TestClient, other_client: TestClient, db: Session, make_user
) -> None:  # type: ignore[no-untyped-def]
    make_user(email="asha@example.com")
    login_client(client, "asha@example.com")
    add_to_cart(client, db, SKU)
    body = place_order(client, email=None).json()
    assert body["access_token"] is None
    assert body["order"]["email"] == "asha@example.com"
    reference = body["order"]["reference"]

    listing = client.get("/api/v1/orders").json()
    assert [o["reference"] for o in listing["items"]] == [reference]
    assert client.get(f"/api/v1/orders/{reference}").status_code == 200

    # Someone else — guest or another customer — gets 404, as if it didn't exist.
    assert other_client.get(f"/api/v1/orders/{reference}").status_code == 404
    make_user(email="ravi@example.com", full_name="Ravi")
    login_client(other_client, "ravi@example.com")
    assert other_client.get(f"/api/v1/orders/{reference}").status_code == 404
    assert other_client.get("/api/v1/orders").json()["items"] == []


def test_guest_order_needs_its_access_token(
    client: TestClient, other_client: TestClient, db: Session
) -> None:
    checkout = buy(client, db)
    reference = checkout["order"]["reference"]
    assert other_client.get(f"/api/v1/orders/{reference}").status_code == 404
    wrong = {"X-Order-Access-Token": "x" * 43}
    assert other_client.get(f"/api/v1/orders/{reference}", headers=wrong).status_code == 404
    shared = other_client.get(f"/api/v1/orders/{reference}", headers=token_headers(checkout))
    assert shared.status_code == 200
    assert shared.json()["status"] == "confirmed"


def test_order_list_requires_sign_in(client: TestClient) -> None:
    assert client.get("/api/v1/orders").status_code == 401
