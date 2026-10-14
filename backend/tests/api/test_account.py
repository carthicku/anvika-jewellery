"""Customer profile, addresses and wishlist — including access control between customers."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import login_client

ADDRESS = {
    "full_name": "Asha Rao",
    "phone": "+91 98765 43210",
    "line1": "12 MG Road",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
}


def test_account_endpoints_require_sign_in(client: TestClient) -> None:
    for method, path in [
        ("get", "/api/v1/me/profile"),
        ("get", "/api/v1/me/addresses"),
        ("post", "/api/v1/me/addresses"),
        ("get", "/api/v1/wishlist"),
        ("get", "/api/v1/auth/sessions"),
    ]:
        response = getattr(client, method)(path, **({"json": ADDRESS} if method == "post" else {}))
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_update_profile(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    response = client.patch(
        "/api/v1/me/profile", json={"full_name": "Asha R", "phone": "9876543210"}
    )
    assert response.status_code == 200
    assert response.json()["phone"] == "+919876543210"
    # Role cannot be changed through the profile.
    sneaky = client.patch("/api/v1/me/profile", json={"full_name": "A", "role": "admin"})
    assert sneaky.status_code == 422


def test_address_crud_and_defaults(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    first = client.post("/api/v1/me/addresses", json=ADDRESS).json()
    assert first["is_default_shipping"] is True  # first address becomes the default
    second = client.post(
        "/api/v1/me/addresses",
        json={
            **ADDRESS,
            "line1": "4 Park Street",
            "city": "Kolkata",
            "state": "West Bengal",
            "pincode": "700016",
            "is_default_shipping": True,
        },
    ).json()
    addresses = client.get("/api/v1/me/addresses").json()
    defaults = [a["id"] for a in addresses if a["is_default_shipping"]]
    assert defaults == [second["id"]]

    updated = client.put(
        f"/api/v1/me/addresses/{first['id']}", json={**ADDRESS, "landmark": "Near metro"}
    )
    assert updated.json()["landmark"] == "Near metro"
    assert client.delete(f"/api/v1/me/addresses/{first['id']}").status_code == 200
    assert len(client.get("/api/v1/me/addresses").json()) == 1


def test_address_validation(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    response = client.post(
        "/api/v1/me/addresses",
        json={**ADDRESS, "pincode": "012345", "state": "Atlantis", "phone": "12345"},
    )
    fields = response.json()["error"]["details"]["fields"]
    assert {"pincode", "state", "phone"} <= set(fields)


def test_customers_cannot_touch_each_others_addresses(  # type: ignore[no-untyped-def]
    client: TestClient, other_client: TestClient, make_user
) -> None:
    make_user("asha@example.com")
    make_user("ravi@example.com", full_name="Ravi K")
    login_client(client, "asha@example.com")
    login_client(other_client, "ravi@example.com")
    address = client.post("/api/v1/me/addresses", json=ADDRESS).json()

    assert other_client.get("/api/v1/me/addresses").json() == []
    for response in (
        other_client.put(f"/api/v1/me/addresses/{address['id']}", json=ADDRESS),
        other_client.delete(f"/api/v1/me/addresses/{address['id']}"),
    ):
        assert response.status_code == 404  # not 403: existence is not revealed
    assert len(client.get("/api/v1/me/addresses").json()) == 1


def test_wishlist_add_remove_and_merge(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    assert client.put("/api/v1/wishlist/om-pendant").status_code == 200
    assert client.put("/api/v1/wishlist/om-pendant").status_code == 200  # idempotent
    merged = client.post(
        "/api/v1/wishlist/merge", json={"slugs": ["rope-chain", "om-pendant", "does-not-exist"]}
    )
    assert merged.status_code == 200
    assert set(client.get("/api/v1/wishlist/slugs").json()) == {"om-pendant", "rope-chain"}
    cards = client.get("/api/v1/wishlist").json()
    assert {c["slug"] for c in cards} == {"om-pendant", "rope-chain"}
    client.delete("/api/v1/wishlist/om-pendant")
    assert client.get("/api/v1/wishlist/slugs").json() == ["rope-chain"]


def test_wishlists_are_private(client: TestClient, other_client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    make_user("ravi@example.com")
    login_client(client, "asha@example.com")
    login_client(other_client, "ravi@example.com")
    client.put("/api/v1/wishlist/om-pendant")
    assert other_client.get("/api/v1/wishlist/slugs").json() == []
