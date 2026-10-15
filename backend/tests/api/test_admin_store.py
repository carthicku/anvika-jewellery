"""Admin store settings API: discounts, coupons, shipping, content, enquiries, settings and staff
user management (J10)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.core.time import utcnow
from app.models import Category, ContactEnquiry, User, UserSession
from app.services import admin_store
from tests.api.order_helpers import add_to_cart, place_order
from tests.conftest import login_client

API = "/api/v1/admin"
SKU = "ANV-RG-002-12"  # 22K ring in "rings", ₹27,402.74 with the seed rate and tax


def unit_price(client: TestClient, db: Session) -> Decimal:
    cart = add_to_cart(client, db, SKU)
    return Decimal(next(line for line in cart["lines"] if line["sku"] == SKU)["unit_price"])


def rings_id(db: Session) -> str:
    return str(db.scalar(select(Category.id).where(Category.slug == "rings")))


# ------------------------------------------------------------------ discounts and coupons


def test_automatic_discount_changes_prices(
    admin: TestClient, staff: TestClient, client: TestClient, db: Session
) -> None:
    body = {
        "name": "Ring week",
        "kind": "percent_off_making",
        "value": "50.00",
        "scope": "category",
        "scope_id": rings_id(db),
        "starts_at": (utcnow() - timedelta(minutes=1)).isoformat(),
    }
    assert staff.post(f"{API}/discounts", json=body).status_code == 403
    created = admin.post(f"{API}/discounts", json=body)
    assert created.status_code == 201, created.text
    assert created.json()["running_now"] is True and created.json()["scope_name"] == "Rings"
    assert unit_price(client, db) < Decimal("27402.74")

    assert admin.post(f"{API}/discounts", json={**body, "value": "150"}).status_code == 422
    assert admin.post(f"{API}/discounts", json={**body, "scope_id": None}).status_code == 422
    ended = admin.put(
        f"{API}/discounts/{created.json()['id']}", json={**body, "is_active": False}
    ).json()
    assert ended["running_now"] is False


def test_coupons_are_created_uppercase_and_track_usage(
    admin: TestClient, client: TestClient, db: Session
) -> None:
    body = {
        "code": "test10",
        "kind": "percent",
        "value": "10",
        "max_discount_amount": "1000.00",
        "starts_at": (utcnow() - timedelta(minutes=1)).isoformat(),
        "usage_limit_per_customer": 1,
    }
    created = admin.post(f"{API}/coupons", json=body)
    assert created.status_code == 201, created.text
    coupon = created.json()
    assert coupon["code"] == "TEST10" and coupon["times_used"] == 0
    assert admin.post(f"{API}/coupons", json=body).status_code == 422  # duplicate code
    assert admin.post(f"{API}/coupons", json={**body, "code": "NO SPACES"}).status_code == 422

    add_to_cart(client, db, SKU)
    assert client.post("/api/v1/cart/coupon", json={"code": "TEST10"}).status_code == 200
    place_order(client)
    listed = next(c for c in admin.get(f"{API}/coupons").json() if c["code"] == "TEST10")
    assert listed["times_reserved"] == 1

    update = {k: v for k, v in body.items() if k != "code"}
    renamed = admin.put(f"{API}/coupons/{coupon['id']}", json={**update, "code": "OTHER"})
    assert renamed.status_code == 422  # the code can't be changed
    paused = admin.put(f"{API}/coupons/{coupon['id']}", json={**update, "is_active": False})
    assert paused.json()["is_active"] is False


# ------------------------------------------------------------------ shipping


def test_shipping_zones_limit_delivery(admin: TestClient, client: TestClient) -> None:
    zone = admin.post(
        f"{API}/shipping/zones",
        json={"name": "Karnataka", "pincode_prefixes": ["56", "57", " 58 "], "extra_days": 1},
    )
    assert zone.status_code == 201, zone.text
    assert zone.json()["pincode_prefixes"] == ["56", "57", "58"]
    far = client.get("/api/v1/shipping/pincode/110001").json()
    near = client.get("/api/v1/shipping/pincode/560001").json()
    assert far["serviceable"] is False and near["serviceable"] is True
    bad = admin.post(f"{API}/shipping/zones", json={"name": "Bad", "pincode_prefixes": ["0123"]})
    assert bad.status_code == 422
    assert admin.delete(f"{API}/shipping/zones/{zone.json()['id']}").status_code == 200
    assert client.get("/api/v1/shipping/pincode/110001").json()["serviceable"] is True


def test_at_least_one_delivery_method_stays_active(admin: TestClient) -> None:
    methods = admin.get(f"{API}/shipping/methods").json()
    assert {m["code"] for m in methods} == {"standard", "express"}

    def body(m: dict[str, object], active: bool) -> dict[str, object]:
        keep = ("code", "name", "description", "fee", "free_above", "min_days", "max_days")
        return {**{k: m[k] for k in keep}, "is_active": active, "sort_order": m["sort_order"]}

    first, second = methods
    assert (
        admin.put(f"{API}/shipping/methods/{first['id']}", json=body(first, False)).status_code
        == 200
    )
    last = admin.put(f"{API}/shipping/methods/{second['id']}", json=body(second, False))
    assert last.status_code == 409 and last.json()["error"]["code"] == "LAST_SHIPPING_METHOD"
    wrong_days = {**body(first, True), "min_days": 5, "max_days": 2}
    assert admin.put(f"{API}/shipping/methods/{first['id']}", json=wrong_days).status_code == 422


# ------------------------------------------------------------------ content and enquiries


def test_staff_edit_content_pages(staff: TestClient, client: TestClient) -> None:
    page = staff.get(f"{API}/content/about").json()
    assert page["is_draft_template"] is True
    saved = staff.put(
        f"{API}/content/about",
        json={
            "title": "About us",
            "summary": "Our story",
            "body_markdown": "# Hello\n\nWritten by the owner.",
            "is_draft_template": False,
        },
    )
    assert saved.status_code == 200, saved.text
    public = client.get("/api/v1/content/about").json()
    assert public["title"] == "About us" and public["is_draft_template"] is False


def test_enquiries_can_be_worked_through(staff: TestClient, db: Session) -> None:
    db.add(
        ContactEnquiry(
            name="Ravi", email="ravi@example.com", subject="Sizing", message="Help with sizes"
        )
    )
    db.commit()
    items = staff.get(f"{API}/enquiries", params={"status": "new"}).json()["items"]
    enquiry = next(e for e in items if e["email"] == "ravi@example.com")
    assert (
        staff.put(f"{API}/enquiries/{enquiry['id']}/status", json={"status": "closed"}).status_code
        == 200
    )
    closed = staff.get(f"{API}/enquiries", params={"status": "closed"}).json()["items"]
    assert any(e["id"] == enquiry["id"] for e in closed)


# ------------------------------------------------------------------ settings


def test_tax_settings_change_prices_and_are_audited(
    admin: TestClient, staff: TestClient, client: TestClient, db: Session
) -> None:
    before = unit_price(client, db)
    tax = {
        "metal_percent": "5.00",
        "making_percent": "5.00",
        "stones_percent": "5.00",
        "shipping_percent": "0.00",
    }
    assert staff.put(f"{API}/settings/tax", json=tax).status_code == 403
    saved = admin.put(f"{API}/settings/tax", json=tax)
    assert saved.status_code == 200, saved.text
    assert saved.json()["tax"]["metal_percent"] == "5.00"
    client.cookies.clear()
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    assert unit_price(client, db) > before
    logs = admin.get(f"{API}/audit-logs", params={"action": "settings.tax"}).json()["items"]
    assert logs[0]["changes"]["metal_percent"] == ["3.00", "5.00"]
    assert admin.put(f"{API}/settings/tax", json={**tax, "metal_percent": "50"}).status_code == 422


def test_store_details_are_validated(admin: TestClient, client: TestClient) -> None:
    current = admin.get(f"{API}/settings").json()["store"]
    assert current["gstin"].startswith("[")  # placeholder until the owner enters it
    bad = admin.put(f"{API}/settings/store", json={**current, "gstin": "NOT-A-GSTIN"})
    assert bad.status_code == 422
    good = admin.put(
        f"{API}/settings/store",
        json={**current, "gstin": "29abcde1234f1z5", "support_email": "help@example.com"},
    )
    assert good.status_code == 200, good.text
    assert good.json()["store"]["gstin"] == "29ABCDE1234F1Z5"
    assert client.get("/api/v1/settings/public").json()["support_email"] == "help@example.com"


def test_announcement_links_must_be_safe(admin: TestClient, client: TestClient) -> None:
    body = {"enabled": True, "text": "Diwali dispatch dates", "link": "javascript:alert(1)"}
    assert admin.put(f"{API}/settings/announcement", json=body).status_code == 422
    assert (
        admin.put(
            f"{API}/settings/announcement", json={**body, "link": "//evil.example"}
        ).status_code
        == 422
    )
    ok = admin.put(f"{API}/settings/announcement", json={**body, "link": "/collections"})
    assert ok.status_code == 200
    assert client.get("/api/v1/settings/public").json()["announcement"]["text"] == (
        "Diwali dispatch dates"
    )


# ------------------------------------------------------------------ staff users


def test_admin_promotes_and_deactivates_staff(
    admin: TestClient, staff: TestClient, other_client: TestClient, db: Session, make_user
) -> None:  # type: ignore[no-untyped-def]
    assert staff.get(f"{API}/users").status_code == 403
    make_user(email="newhire@example.com", full_name="New Hire")
    login_client(other_client, "newhire@example.com")
    assert other_client.get(f"{API}/dashboard").status_code == 403

    promoted = admin.post(
        f"{API}/users/promote", json={"email": "NewHire@example.com", "role": "staff"}
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "staff"
    hire = db.scalar(select(User).where(User.email == "newhire@example.com"))
    assert hire is not None
    sessions = db.scalars(select(UserSession).where(UserSession.user_id == hire.id)).all()
    assert all(s.revoked_at is not None for s in sessions)  # signed out after a role change
    login_client(other_client, "newhire@example.com")
    assert other_client.get(f"{API}/dashboard").status_code == 200

    off = admin.put(f"{API}/users/{hire.id}/active", json={"is_active": False})
    assert off.json()["is_active"] is False
    assert other_client.get(f"{API}/dashboard").status_code in (401, 403)

    me = db.scalar(select(User).where(User.email == "owner@example.com"))
    assert me is not None
    assert admin.put(f"{API}/users/{me.id}/role", json={"role": "staff"}).status_code == 409
    assert admin.put(f"{API}/users/{me.id}/active", json={"is_active": False}).status_code == 409
    missing = admin.post(
        f"{API}/users/promote", json={"email": "nobody@example.com", "role": "staff"}
    )
    assert missing.status_code == 404


def test_the_last_admin_cannot_be_removed(db: Session, make_user) -> None:  # type: ignore[no-untyped-def]
    only_admin = make_user(email="solo@example.com", role="admin")
    other_actor = make_user(email="helper@example.com", role="staff")
    # Remove every other admin from consideration, then try to demote the only one left.
    for user in db.scalars(select(User).where(User.role == "admin", User.id != only_admin.id)):
        user.role = "customer"
    db.commit()
    with pytest.raises(Conflict):
        admin_store.set_role(db, other_actor, only_admin, "customer", None)
    with pytest.raises(Conflict):
        admin_store.set_active(db, other_actor, only_admin, False, None)
