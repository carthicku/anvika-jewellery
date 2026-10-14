"""Cart API: backend pricing, stock limits, ownership, price-change acceptance, coupons, merge."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import GoldRate, InventoryLevel, Product, ProductVariant
from tests.conftest import login_client

API = "/api/v1/cart"


def variant_id(db: Session, sku: str) -> str:
    vid = db.scalar(select(ProductVariant.id).where(ProductVariant.sku == sku))
    assert vid is not None
    return str(vid)


def add(client: TestClient, db: Session, sku: str, quantity: int = 1):  # type: ignore[no-untyped-def]
    return client.post(
        f"{API}/items", json={"variant_id": variant_id(db, sku), "quantity": quantity}
    )


def raise_22k_rate(db: Session, rate: str = "8000.00") -> None:
    db.add(
        GoldRate(
            purity="22K", rate_per_gram=Decimal(rate), effective_from=utcnow(), source_note="test"
        )
    )
    db.commit()


# ------------------------------------------------------------------ basics


def test_empty_cart_for_a_new_visitor(client: TestClient) -> None:
    body = client.get(API).json()
    assert body == {
        "lines": [],
        "item_count": 0,
        "totals": None,
        "coupon": None,
        "can_checkout": False,
        "blocking_issues": [],
        "notices": [],
    }


def test_guest_add_sets_httponly_cart_cookie_and_prices_on_server(
    client: TestClient, db: Session
) -> None:
    response = add(client, db, "ANV-RG-002-12", 2)
    assert response.status_code == 200, response.text
    cookie = next(c for c in response.headers.get_list("set-cookie") if c.startswith("cart_token="))
    assert "HttpOnly" in cookie and "Path=/api" in cookie
    body = response.json()
    line = body["lines"][0]
    assert line["unit_price"] == "27402.74"  # Everyday Gold Band size 12 (see catalogue tests)
    assert line["quantity"] == 2
    assert line["line_total"] == "54805.48"
    totals = body["totals"]
    # Free standard delivery above ₹25,000 (seeded shipping method).
    assert totals["shipping_fee"] == "0.00"
    assert Decimal(totals["grand_total"]) % 1 == 0
    rows = totals["breakdown"]
    assert sum(Decimal(r["amount"]) for r in rows[:-1]) == Decimal(rows[-1]["amount"])
    assert body["can_checkout"] is True and body["item_count"] == 2
    # The cart persists for this browser.
    assert client.get(API).json()["item_count"] == 2


def test_browser_supplied_prices_are_rejected(client: TestClient, db: Session) -> None:
    response = client.post(
        f"{API}/items",
        json={"variant_id": variant_id(db, "ANV-PD-001"), "quantity": 1, "unit_price": "1.00"},
    )
    assert response.status_code == 422


def test_adding_again_combines_quantities_and_update_and_remove(
    client: TestClient, db: Session
) -> None:
    add(client, db, "ANV-PD-001")
    body = add(client, db, "ANV-PD-001", 2).json()
    assert len(body["lines"]) == 1 and body["lines"][0]["quantity"] == 3
    line_id = body["lines"][0]["id"]
    assert client.patch(f"{API}/items/{line_id}", json={"quantity": 1}).json()["item_count"] == 1
    assert client.delete(f"{API}/items/{line_id}").json()["lines"] == []


def test_stock_and_quantity_limits(client: TestClient, db: Session) -> None:
    # Heritage Bridal Necklace: one-of-a-kind (stock 1).
    over = add(client, db, "ANV-NK-001", 2)
    assert over.status_code == 409 and over.json()["error"]["code"] == "OUT_OF_STOCK"
    assert over.json()["error"]["details"] == {"available": 1}
    sold_out = add(client, db, "ANV-ER-004")  # Peacock Drops, stock 0
    assert sold_out.json()["error"]["code"] == "OUT_OF_STOCK"
    too_many = client.post(
        f"{API}/items", json={"variant_id": variant_id(db, "ANV-PD-001"), "quantity": 11}
    )
    assert too_many.status_code == 422


def test_cannot_add_inactive_or_unpriceable_products(client: TestClient, db: Session) -> None:
    db.execute(update(Product).where(Product.slug == "om-pendant").values(status="draft"))
    db.commit()
    assert add(client, db, "ANV-PD-001").status_code == 404
    db.execute(update(Product).where(Product.slug == "om-pendant").values(status="active"))
    db.execute(GoldRate.__table__.delete().where(GoldRate.purity == "22K"))
    db.commit()
    response = add(client, db, "ANV-PD-001")
    assert response.status_code == 409 and response.json()["error"]["code"] == "PRICE_UNAVAILABLE"


def test_customers_cannot_change_other_carts(
    client: TestClient, other_client: TestClient, db: Session
) -> None:
    line_id = add(client, db, "ANV-PD-001").json()["lines"][0]["id"]
    assert other_client.patch(f"{API}/items/{line_id}", json={"quantity": 2}).status_code == 404
    assert other_client.delete(f"{API}/items/{line_id}").status_code == 404
    assert client.get(API).json()["item_count"] == 1


# ------------------------------------------------------------------ price changes


def test_price_increase_blocks_checkout_until_accepted(client: TestClient, db: Session) -> None:
    add(client, db, "ANV-PD-001")
    raise_22k_rate(db)
    body = client.get(API).json()
    line = body["lines"][0]
    assert line["price_change"] == "increased"
    assert Decimal(line["unit_price"]) > Decimal(line["accepted_unit_price"])
    assert body["can_checkout"] is False
    assert any("has gone up" in issue for issue in body["blocking_issues"])

    accepted = client.post(f"{API}/accept-prices").json()
    assert accepted["can_checkout"] is True
    assert accepted["lines"][0]["price_change"] is None


def test_price_decrease_is_good_news_and_does_not_block(client: TestClient, db: Session) -> None:
    add(client, db, "ANV-PD-001")
    raise_22k_rate(db, "6000.00")
    body = client.get(API).json()
    assert body["lines"][0]["price_change"] == "decreased"
    assert body["can_checkout"] is True
    assert body["notices"] and body["notices"][0].startswith("Good news")


def test_stock_problems_block_checkout(client: TestClient, db: Session) -> None:
    add(client, db, "ANV-PD-001", 3)
    db.execute(
        update(InventoryLevel)
        .where(InventoryLevel.variant_id == variant_id(db, "ANV-PD-001"))
        .values(on_hand=2)
    )
    db.commit()
    body = client.get(API).json()
    assert body["lines"][0]["issue"] == "insufficient_stock"
    assert body["lines"][0]["max_quantity"] == 2
    assert body["can_checkout"] is False
    assert body["totals"] is None  # nothing purchasable left to total


# ------------------------------------------------------------------ coupons


def test_valid_coupon_applies_with_cap(client: TestClient, db: Session) -> None:
    add(client, db, "ANV-NK-001")  # ~₹4.2 lakh necklace: 5% would exceed the ₹2,500 cap
    body = client.post(f"{API}/coupon", json={"code": "welcome5"}).json()
    assert body["coupon"] == {"code": "WELCOME5", "applied": True, "message": "You save ₹2,500."}
    assert body["totals"]["coupon_discount"] == "2500.00"
    removed = client.delete(f"{API}/coupon").json()
    assert removed["coupon"] is None and removed["totals"]["coupon_discount"] == "0.00"


def test_invalid_coupons_explain_why(client: TestClient, db: Session) -> None:
    add(client, db, "ANV-PD-001")
    unknown = client.post(f"{API}/coupon", json={"code": "NOPE"})
    expired = client.post(f"{API}/coupon", json={"code": "EXPIRED10"})
    assert unknown.status_code == expired.status_code == 422
    assert unknown.json()["error"]["code"] == "COUPON_NOT_FOUND"
    assert expired.json()["error"]["code"] == "COUPON_EXPIRED"
    assert expired.json()["error"]["message"] == "This coupon has expired."


def test_coupon_below_minimum_is_kept_but_not_applied(client: TestClient, db: Session) -> None:
    db.execute(
        update(ProductVariant)
        .where(ProductVariant.sku == "ANV-PD-003")
        .values(fixed_price=Decimal("5000.00"))
    )
    db.commit()
    add(client, db, "ANV-PD-003")
    body = client.post(f"{API}/coupon", json={"code": "WELCOME5"}).json()
    assert body["coupon"]["applied"] is False
    assert (
        body["coupon"]["message"] == "Your order needs to reach ₹10,000 before this coupon applies."
    )
    assert body["totals"]["coupon_discount"] == "0.00"


# ------------------------------------------------------------------ guest → account


def test_guest_cart_merges_into_account_at_sign_in(
    client: TestClient, db: Session, make_user
) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    add(client, db, "ANV-PD-001", 2)
    client.post(f"{API}/coupon", json={"code": "WELCOME5"})
    login_client(client, "asha@example.com")
    body = client.get(API).json()
    assert body["item_count"] == 2
    assert body["coupon"]["code"] == "WELCOME5"
    # The guest cookie was cleared; signing out leaves an empty guest cart.
    client.post("/api/v1/auth/logout")
    client.headers["X-CSRF-Token"] = client.cookies["csrf_token"]
    assert client.get(API).json()["item_count"] == 0


def test_merge_combines_quantities_up_to_the_limit(
    client: TestClient, other_client: TestClient, db: Session, make_user
) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(other_client, "asha@example.com")
    add(other_client, db, "ANV-PD-001", 6)  # already in the account cart
    add(client, db, "ANV-PD-001", 6)  # added as a guest on another device
    login_client(client, "asha@example.com")
    assert client.get(API).json()["lines"][0]["quantity"] == 10


def test_unknown_cart_token_gives_an_empty_cart(client: TestClient) -> None:
    client.cookies.set("cart_token", "x" * 43, path="/api")
    assert client.get(API).json()["item_count"] == 0
