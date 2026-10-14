"""Authentication: registration, login, sessions, refresh rotation, password and email flows."""

from __future__ import annotations

import re
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.core.time import utcnow
from app.models import EmailOutbox, User, UserSession, UserToken
from app.services.email import MEMORY_OUTBOX
from tests.conftest import PASSWORD, login_client, replace_cookie, sync_csrf

API = "/api/v1/auth"
NEW_USER = {"full_name": "Asha Rao", "email": "Asha@Example.com", "password": PASSWORD}


def latest_link(kind: str) -> str:
    """Token from the most recent email whose link contains `kind` (from the memory backend)."""
    for message in reversed(MEMORY_OUTBOX):
        body = message.get_body(("plain",))
        assert body is not None
        match = re.search(rf"/{kind}\?token=([\w-]+)", body.get_content())
        if match:
            return match.group(1)
    raise AssertionError(f"no {kind} email found")


# ------------------------------------------------------------------ registration


def test_register_creates_customer_and_signs_in(client: TestClient, db: Session) -> None:
    response = client.post(f"{API}/register", json={**NEW_USER, "phone": "98765 43210"})
    assert response.status_code == 201, response.text
    user = response.json()["user"]
    assert user["email"] == "asha@example.com"
    assert user["role"] == "customer" and user["permissions"] == []
    assert user["phone"] == "+919876543210"
    assert user["email_verified"] is False

    # Cookies are HttpOnly session cookies; the body never contains tokens.
    assert "access_token" not in response.text and "refresh_token" not in response.text
    set_cookie = response.headers.get_list("set-cookie")
    access = next(c for c in set_cookie if c.startswith("access_token="))
    refresh = next(c for c in set_cookie if c.startswith("refresh_token="))
    assert "HttpOnly" in access and "SameSite=lax" in access
    assert "HttpOnly" in refresh and "SameSite=strict" in refresh and "Path=/api/v1/auth" in refresh

    assert client.get(f"{API}/me").json()["user"]["email"] == "asha@example.com"
    stored = db.scalar(select(User).where(User.email == "asha@example.com"))
    assert stored is not None and stored.password_hash.startswith("$argon2id$")


def test_register_sends_verification_email_and_verifies(client: TestClient) -> None:
    client.post(f"{API}/register", json=NEW_USER)
    sync_csrf(client)
    assert len(MEMORY_OUTBOX) == 1
    assert MEMORY_OUTBOX[0]["To"] == "asha@example.com"
    token = latest_link("verify-email")
    assert client.post(f"{API}/verify-email", json={"token": token}).status_code == 200
    assert client.get(f"{API}/me").json()["user"]["email_verified"] is True
    # Single use.
    again = client.post(f"{API}/verify-email", json={"token": token})
    assert again.status_code == 400 and again.json()["error"]["code"] == "INVALID_TOKEN"


def test_sent_email_context_is_cleared(client: TestClient, db: Session) -> None:
    client.post(f"{API}/register", json=NEW_USER)
    row = db.scalar(select(EmailOutbox))
    assert row is not None and row.status == "written_to_sink" and row.context == {}


def test_register_duplicate_email(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    response = client.post(f"{API}/register", json=NEW_USER)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_IN_USE"


def test_register_rejects_weak_password_and_bad_input(client: TestClient) -> None:
    weak = client.post(f"{API}/register", json={**NEW_USER, "password": "1234567890"})
    assert weak.status_code == 422
    assert "password" in weak.json()["error"]["details"]["fields"]
    same_as_email = client.post(
        f"{API}/register", json={**NEW_USER, "password": "asha@example.com"}
    )
    assert same_as_email.status_code == 422
    bad = client.post(
        f"{API}/register",
        json={**NEW_USER, "email": "nope", "phone": "12345", "role": "admin"},
    )
    fields = bad.json()["error"]["details"]["fields"]
    assert {"email", "phone", "role"} <= set(fields)  # unknown "role" field is rejected


# ------------------------------------------------------------------ login


def test_login_success_and_wrong_password_are_distinct(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    wrong = client.post(f"{API}/login", json={"email": "asha@example.com", "password": "nope-nope"})
    unknown = client.post(
        f"{API}/login", json={"email": "who@example.com", "password": "nope-nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"
    ok = client.post(f"{API}/login", json={"email": "ASHA@example.com", "password": PASSWORD})
    assert ok.status_code == 200


def test_inactive_user_cannot_log_in(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com", is_active=False)
    response = client.post(f"{API}/login", json={"email": "asha@example.com", "password": PASSWORD})
    assert response.status_code == 401


def test_login_is_rate_limited_per_account(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    codes = [
        client.post(
            f"{API}/login", json={"email": "asha@example.com", "password": "x" * 10}
        ).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
    # Even the right password is refused while limited.
    blocked = client.post(f"{API}/login", json={"email": "asha@example.com", "password": PASSWORD})
    assert blocked.status_code == 429


# ------------------------------------------------------------------ sessions


def test_me_is_null_for_guests(client: TestClient) -> None:
    assert client.get(f"{API}/me").json() == {"user": None}


def test_logout_revokes_session_immediately(client: TestClient, make_user, db: Session) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    access = client.cookies["access_token"]
    assert client.post(f"{API}/logout").status_code == 200
    assert client.get(f"{API}/me").json() == {"user": None}
    # Replaying the old (still unexpired) access token no longer works.
    replace_cookie(client, "access_token", access)
    assert client.get(f"{API}/me").json() == {"user": None}
    assert client.get("/api/v1/me/profile").status_code == 401


def test_expired_access_token_asks_for_refresh(client: TestClient, make_user, settings) -> None:  # type: ignore[no-untyped-def]
    from app.core.security import create_access_token

    user = make_user("asha@example.com")
    login_client(client, "asha@example.com")
    session_id = client.app.state.session_factory().scalar(  # type: ignore[attr-defined]
        select(UserSession.id).where(UserSession.user_id == user.id)
    )
    expired, _ = create_access_token(
        settings, user_id=user.id, session_id=session_id, now=utcnow() - timedelta(hours=1)
    )
    replace_cookie(client, "access_token", expired)
    response = client.get("/api/v1/me/profile")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"
    # Refresh issues new tokens and the request works again.
    assert client.post(f"{API}/refresh").status_code == 200
    sync_csrf(client)
    assert client.get("/api/v1/me/profile").status_code == 200


def test_tampered_access_token_is_treated_as_guest(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    token = client.cookies["access_token"]
    replace_cookie(client, "access_token", token[:-4] + "AAAA")
    assert client.get(f"{API}/me").json() == {"user": None}


def test_refresh_rotates_and_detects_reuse(client: TestClient, make_user, db: Session) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    first = client.cookies.get("refresh_token", path="/api/v1/auth")
    assert client.post(f"{API}/refresh").status_code == 200
    sync_csrf(client)
    second = client.cookies.get("refresh_token", path="/api/v1/auth")
    assert first and second and first != second

    # Simulate a thief replaying the old token later (outside the multi-tab race window).
    session = db.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == hash_token(second))
    )
    assert session is not None
    session.last_used_at = utcnow() - timedelta(minutes=5)
    db.commit()
    replace_cookie(client, "refresh_token", first, path="/api/v1/auth")
    replay = client.post(f"{API}/refresh")
    assert replay.status_code == 401
    db.refresh(session)
    assert session.revoked_at is not None and session.revoked_reason == "refresh_token_reuse"
    # The legitimate token is now useless too.
    client.cookies.set("refresh_token", second, path="/api/v1/auth")
    assert client.post(f"{API}/refresh").status_code == 401


def test_concurrent_refresh_from_two_tabs_is_not_treated_as_theft(
    client: TestClient, make_user, db: Session
) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    first = client.cookies.get("refresh_token", path="/api/v1/auth")
    assert client.post(f"{API}/refresh").status_code == 200
    sync_csrf(client)
    replace_cookie(client, "refresh_token", first, path="/api/v1/auth")
    race = client.post(f"{API}/refresh")
    assert race.status_code == 409 and race.json()["error"]["code"] == "REFRESH_RACE"
    assert db.scalar(select(UserSession.revoked_at)) is None


def test_list_and_revoke_sessions(client: TestClient, other_client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    login_client(other_client, "asha@example.com")
    sessions = client.get(f"{API}/sessions").json()
    assert len(sessions) == 2
    other = next(s for s in sessions if not s["current"])
    assert client.delete(f"{API}/sessions/{other['id']}").status_code == 200
    assert other_client.get(f"{API}/me").json() == {"user": None}
    assert client.get(f"{API}/me").json()["user"] is not None


def test_logout_all(client: TestClient, other_client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    login_client(other_client, "asha@example.com")
    assert client.post(f"{API}/logout-all").status_code == 200
    assert other_client.get(f"{API}/me").json() == {"user": None}


# ------------------------------------------------------------------ passwords


def test_forgot_password_never_reveals_accounts(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    known = client.post(f"{API}/forgot-password", json={"email": "asha@example.com"})
    unknown = client.post(f"{API}/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert [m["To"] for m in MEMORY_OUTBOX] == ["asha@example.com"]


def test_reset_password_flow(
    client: TestClient, other_client: TestClient, make_user, db: Session
) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(other_client, "asha@example.com")
    client.post(f"{API}/forgot-password", json={"email": "asha@example.com"})
    token = latest_link("reset-password")

    weak = client.post(f"{API}/reset-password", json={"token": token, "password": "short"})
    assert weak.status_code == 422

    new_password = "a brand new passphrase"
    ok = client.post(f"{API}/reset-password", json={"token": token, "password": new_password})
    assert ok.status_code == 200
    # All existing sessions are signed out; the new password works; the token is single-use.
    assert other_client.get(f"{API}/me").json() == {"user": None}
    login_client(client, "asha@example.com", new_password)
    reused = client.post(f"{API}/reset-password", json={"token": token, "password": new_password})
    assert reused.json()["error"]["code"] == "INVALID_TOKEN"
    assert any(m["Subject"].endswith("password was changed") for m in MEMORY_OUTBOX)


def test_reset_token_expires(client: TestClient, make_user, db: Session) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    client.post(f"{API}/forgot-password", json={"email": "asha@example.com"})
    token = latest_link("reset-password")
    row = db.scalar(select(UserToken).where(UserToken.token_hash == hash_token(token)))
    assert row is not None
    row.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    response = client.post(
        f"{API}/reset-password", json={"token": token, "password": "another fine pass"}
    )
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_only_newest_reset_link_works(client: TestClient, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    client.post(f"{API}/forgot-password", json={"email": "asha@example.com"})
    old = latest_link("reset-password")
    client.post(f"{API}/forgot-password", json={"email": "asha@example.com"})
    response = client.post(
        f"{API}/reset-password", json={"token": old, "password": "another fine pass"}
    )
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_change_password_keeps_current_session_only(
    client: TestClient, other_client: TestClient, make_user
) -> None:  # type: ignore[no-untyped-def]
    make_user("asha@example.com")
    login_client(client, "asha@example.com")
    login_client(other_client, "asha@example.com")
    wrong = client.post(
        f"{API}/change-password",
        json={"current_password": "not it at all", "new_password": "a new long password"},
    )
    assert wrong.status_code == 422
    assert "current_password" in wrong.json()["error"]["details"]["fields"]
    ok = client.post(
        f"{API}/change-password",
        json={"current_password": PASSWORD, "new_password": "a new long password"},
    )
    assert ok.status_code == 200
    assert client.get(f"{API}/me").json()["user"] is not None
    assert other_client.get(f"{API}/me").json() == {"user": None}


def test_password_hash_is_upgraded_on_login(client: TestClient, make_user, db: Session) -> None:  # type: ignore[no-untyped-def]
    from argon2 import PasswordHasher

    user = make_user("asha@example.com")
    weaker = PasswordHasher(time_cost=1, memory_cost=512, parallelism=1).hash(PASSWORD)
    user.password_hash = weaker
    db.commit()
    login_client(client, "asha@example.com")
    db.refresh(user)
    assert user.password_hash != weaker
    assert "m=512," not in user.password_hash
