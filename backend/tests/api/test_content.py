"""Public settings, content pages, PIN-code checks, contact form and newsletter."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ContactEnquiry, NewsletterSubscriber, ShippingZone

API = "/api/v1"

VALID_CONTACT = {
    "name": "Asha Rao",
    "email": "Asha@Example.com",
    "phone": "+91 98765 43210",
    "subject": "Ring sizing",
    "message": "Could you help me choose the right ring size?",
    "elapsed_seconds": 20,
}


def test_public_settings_show_placeholders_not_invented_facts(client: TestClient) -> None:
    body = client.get(f"{API}/settings/public").json()
    assert body["store_name"] == "Anvika"
    assert body["business_address"].startswith("[")
    assert body["payment_mode"] == "simulator"
    assert body["announcement"]["enabled"] is True


def test_content_page_is_marked_as_draft(client: TestClient) -> None:
    body = client.get(f"{API}/content/refund-policy").json()
    assert body["is_draft_template"] is True
    assert "lawyer" in body["body_markdown"]
    assert client.get(f"{API}/content/nope").status_code == 404


# ------------------------------------------------------------------ PIN codes


def test_valid_pincode_is_serviceable_with_options(client: TestClient) -> None:
    body = client.get(f"{API}/shipping/pincode/560001").json()
    assert body["serviceable"] is True
    codes = [o["code"] for o in body["options"]]
    assert codes == ["standard", "express"]
    standard = body["options"][0]
    assert standard["fee"] == "199.00" and standard["free_above"] == "25000.00"
    assert standard["estimated_from"] <= standard["estimated_to"]


def test_invalid_pincodes_are_rejected(client: TestClient) -> None:
    for pin in ("012345", "12345", "1234567", "abcdef", "56 001"):
        response = client.get(f"{API}/shipping/pincode/{pin}")
        assert response.status_code == 422, pin
        assert "pincode" in response.json()["error"]["details"]["fields"]


def test_zones_restrict_serviceability(client: TestClient, db: Session) -> None:
    db.add(ShippingZone(name="Karnataka", pincode_prefixes=["56", "57"], extra_days=1))
    db.commit()
    inside = client.get(f"{API}/shipping/pincode/560001").json()
    outside = client.get(f"{API}/shipping/pincode/110001").json()
    assert inside["serviceable"] is True
    assert inside["options"][0]["min_days"] == 5  # 4 + 1 extra day
    assert outside == {
        "pincode": "110001",
        "serviceable": False,
        "message": "Sorry, we don't deliver to this PIN code yet.",
        "options": [],
    }


# ------------------------------------------------------------------ contact form


def _enquiries(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(ContactEnquiry)) or 0


def test_contact_enquiry_is_stored(client: TestClient, db: Session) -> None:
    response = client.post(f"{API}/contact", json=VALID_CONTACT)
    assert response.status_code == 202
    enquiry = db.scalar(select(ContactEnquiry))
    assert enquiry is not None
    assert enquiry.email == "asha@example.com"
    assert enquiry.phone == "+919876543210"


def test_contact_spam_is_silently_dropped(client: TestClient, db: Session) -> None:
    honeypot = client.post(f"{API}/contact", json={**VALID_CONTACT, "website": "http://spam"})
    too_fast = client.post(f"{API}/contact", json={**VALID_CONTACT, "elapsed_seconds": 0})
    assert honeypot.status_code == too_fast.status_code == 202
    assert _enquiries(db) == 0


def test_contact_validation(client: TestClient) -> None:
    response = client.post(
        f"{API}/contact",
        json={**VALID_CONTACT, "email": "not-an-email", "message": "short", "unknown": 1},
    )
    assert response.status_code == 422
    fields = response.json()["error"]["details"]["fields"]
    assert {"email", "message", "unknown"} <= set(fields)


def test_contact_is_rate_limited(client: TestClient) -> None:
    statuses = [client.post(f"{API}/contact", json=VALID_CONTACT).status_code for _ in range(6)]
    assert statuses[:5] == [202] * 5
    assert statuses[5] == 429
    limited = client.post(f"{API}/contact", json=VALID_CONTACT)
    assert int(limited.headers["retry-after"]) > 0
    assert limited.json()["error"]["code"] == "RATE_LIMITED"


# ------------------------------------------------------------------ newsletter


def test_newsletter_subscribe_is_idempotent_and_private(client: TestClient, db: Session) -> None:
    payload = {"email": "Reader@Example.com", "consent": True}
    first = client.post(f"{API}/newsletter/subscribe", json=payload)
    second = client.post(f"{API}/newsletter/subscribe", json=payload)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()  # no hint whether the address already existed
    count = db.scalar(select(func.count()).select_from(NewsletterSubscriber))
    assert count == 1


def test_newsletter_requires_consent(client: TestClient) -> None:
    response = client.post(
        f"{API}/newsletter/subscribe", json={"email": "a@b.co", "consent": False}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONSENT_REQUIRED"


def test_newsletter_unsubscribe_with_invalid_token(client: TestClient) -> None:
    response = client.post(f"{API}/newsletter/unsubscribe", json={"token": "x" * 32})
    assert response.status_code == 404
