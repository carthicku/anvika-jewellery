"""Helpers shared by the checkout / payment / order tests."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InventoryLevel, ProductVariant

ADDRESS: dict[str, Any] = {
    "full_name": "Asha Rao",
    "phone": "9876543210",
    "line1": "12 MG Road",
    "line2": "Flat 4B",
    "landmark": None,
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
}


def variant(db: Session, sku: str) -> ProductVariant:
    found = db.scalar(select(ProductVariant).where(ProductVariant.sku == sku))
    assert found is not None
    return found


def level(db: Session, sku: str) -> InventoryLevel:
    row = db.get(InventoryLevel, variant(db, sku).id, populate_existing=True)
    assert row is not None
    return row


def add_to_cart(client: TestClient, db: Session, sku: str, quantity: int = 1) -> dict[str, Any]:
    response = client.post(
        "/api/v1/cart/items", json={"variant_id": str(variant(db, sku).id), "quantity": quantity}
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def quote(
    client: TestClient, pincode: str = "560001", method: str | None = "standard"
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/checkout/quote", json={"pincode": pincode, "shipping_method": method}
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def new_key() -> str:
    return uuid.uuid4().hex


def place_order(
    client: TestClient,
    *,
    key: str | None = None,
    email: str | None = "guest@example.com",
    expected_total: str | None = None,
    method: str = "standard",
    address: dict[str, Any] | None = None,
    **extra: Any,
):  # type: ignore[no-untyped-def]
    if expected_total is None:
        expected_total = quote(client, method=method)["cart"]["totals"]["grand_total"]
    body: dict[str, Any] = {
        "shipping_address": address or ADDRESS,
        "shipping_method": method,
        "expected_total": expected_total,
        "terms_accepted": True,
        **extra,
    }
    if email is not None:
        body["email"] = email
    return client.post(
        "/api/v1/checkout/orders", json=body, headers={"Idempotency-Key": key or new_key()}
    )


def token_headers(checkout: dict[str, Any]) -> dict[str, str]:
    token = checkout.get("access_token")
    return {"X-Order-Access-Token": token} if token else {}


def simulate(
    client: TestClient, checkout: dict[str, Any], outcome: str = "success"
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/payments/simulator/pay",
        json={
            "reference": checkout["order"]["reference"],
            "provider_order_id": checkout["payment"]["provider_order_id"],
            "outcome": outcome,
        },
        headers=token_headers(checkout),
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def verify(client: TestClient, checkout: dict[str, Any], sim: dict[str, Any]):  # type: ignore[no-untyped-def]
    return client.post(
        "/api/v1/payments/verify",
        json={
            "reference": checkout["order"]["reference"],
            "provider_order_id": sim["provider_order_id"],
            "provider_payment_id": sim["provider_payment_id"],
            "signature": sim["signature"],
        },
        headers=token_headers(checkout),
    )


def buy(
    client: TestClient, db: Session, sku: str = "ANV-RG-002-12", quantity: int = 1
) -> dict[str, Any]:
    """Add to cart, place the order and pay successfully with the simulator."""
    add_to_cart(client, db, sku, quantity)
    response = place_order(client)
    assert response.status_code == 200, response.text
    checkout: dict[str, Any] = response.json()
    paid = verify(client, checkout, simulate(client, checkout))
    assert paid.status_code == 200, paid.text
    assert paid.json()["outcome"] == "paid"
    return checkout
