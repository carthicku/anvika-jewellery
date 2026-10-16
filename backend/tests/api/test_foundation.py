"""Foundation behaviour: health, error format, CSRF, security headers, body size limit."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import Conflict


def test_health_is_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "not_checked", "migration": None}


def test_deep_health_checks_database_and_reports_migration(client: TestClient) -> None:
    body = client.get("/api/v1/health", params={"deep": "true"}).json()
    assert body["database"] == "ok"
    assert body["migration"]  # a revision id from alembic_version


def test_unknown_route_uses_standard_error_format(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["message"]
    assert error["request_id"] == response.headers["x-request-id"]


def test_validation_errors_list_fields(client: TestClient) -> None:
    response = client.get("/api/v1/health", params={"deep": "not-a-bool"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "deep" in error["details"]["fields"]


def test_app_errors_and_unexpected_errors_are_formatted(app: FastAPI) -> None:
    @app.get("/api/v1/_test/conflict")
    def conflict() -> None:
        raise Conflict("Already done.", details={"hint": "x"})

    @app.get("/api/v1/_test/crash")
    def crash() -> None:
        raise RuntimeError("secret internal detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        conflict_response = client.get("/api/v1/_test/conflict")
        assert conflict_response.status_code == 409
        assert conflict_response.json()["error"]["details"] == {"hint": "x"}

        crash_response = client.get("/api/v1/_test/crash")
        assert crash_response.status_code == 500
        body = crash_response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert "secret internal detail" not in crash_response.text


def test_unsafe_request_without_csrf_token_is_rejected(raw_client: TestClient) -> None:
    response = raw_client.post("/api/v1/health")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_FAILED"


def test_unsafe_request_with_mismatched_csrf_token_is_rejected(raw_client: TestClient) -> None:
    raw_client.get("/api/v1/auth/csrf")
    response = raw_client.post("/api/v1/health", headers={"X-CSRF-Token": "wrong"})
    assert response.status_code == 403


def test_unsafe_request_with_valid_csrf_token_passes_csrf(client: TestClient) -> None:
    # Health has no POST handler, so passing CSRF means reaching the router (405), not 403.
    assert client.post("/api/v1/health").status_code == 405


def test_unsafe_request_from_foreign_origin_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_FAILED"


def test_webhooks_are_exempt_from_csrf(raw_client: TestClient) -> None:
    # No CSRF header: the request still reaches the webhook, which rejects the missing HMAC
    # signature itself (400, not the CSRF middleware's 403).
    response = raw_client.post("/api/v1/webhooks/razorpay", content=b"{}")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "WEBHOOK_SIGNATURE_INVALID"


def test_csrf_endpoint_reuses_existing_cookie(raw_client: TestClient) -> None:
    first = raw_client.get("/api/v1/auth/csrf").json()["csrf_token"]
    second = raw_client.get("/api/v1/auth/csrf").json()["csrf_token"]
    assert first == second
    assert raw_client.cookies["csrf_token"] == first


def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "strict-transport-security" not in response.headers  # only in production


def test_request_id_is_echoed_when_well_formed(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "abcdef12-3456"})
    assert response.headers["x-request-id"] == "abcdef12-3456"
    injected = client.get("/api/v1/health", headers={"X-Request-ID": "bad id\r\nx"})
    assert injected.headers["x-request-id"] != "bad id\r\nx"


def test_oversized_body_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/health",
        content=b"x" * 1_100_000,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_cors_allows_only_listed_origins(client: TestClient) -> None:
    preflight = {"Access-Control-Request-Method": "POST"}
    allowed = client.options(
        "/api/v1/cart/items", headers={"Origin": "http://localhost:5180", **preflight}
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5180"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    foreign = client.options(
        "/api/v1/cart/items", headers={"Origin": "https://evil.example", **preflight}
    )
    assert "access-control-allow-origin" not in foreign.headers
    simple = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in simple.headers


def test_logs_never_contain_secrets() -> None:
    import json
    import logging

    from app.core.logging import JsonFormatter, TextFormatter

    record = logging.makeLogRecord(
        {
            "msg": "login attempt",
            "levelname": "INFO",
            "password": "hunter2-secret",
            "refresh_token": "rt-abc",
            "headers": {"Authorization": "Bearer xyz", "Cookie": "access=1", "Accept": "json"},
            "razorpay_signature": "sig",
            "card_number": "4111",
            "order": "ANV-1",
        }
    )
    line = JsonFormatter().format(record)
    data = json.loads(line)
    for secret in ("hunter2-secret", "rt-abc", "Bearer xyz", "access=1", 'sig"', "4111"):
        assert secret not in line, secret
    assert data["headers"]["Accept"] == "json" and data["order"] == "ANV-1"
    text = TextFormatter("%(message)s").format(record)
    assert "hunter2" not in text and "Bearer xyz" not in text and "[REDACTED]" in text


def test_client_ip_trusts_only_the_configured_proxy_hops(app: FastAPI) -> None:
    from starlette.requests import Request

    from app.core.client_ip import client_ip

    def ip(forwarded: str | None, trusted: int) -> str:
        app.state.settings = app.state.settings.model_copy(update={"trusted_proxy_count": trusted})
        headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
        scope = {"type": "http", "app": app, "headers": headers, "client": ("10.0.0.2", 1234)}
        return client_ip(Request(scope))

    # Without a trusted proxy the header is ignored (anyone can send it).
    assert ip("1.2.3.4", 0) == "10.0.0.2"
    # Behind one proxy (Caddy overwrites the header), the last hop is the real visitor; anything a
    # visitor prepends is ignored.
    assert ip("6.6.6.6, 203.0.113.9", 1) == "203.0.113.9"
    assert ip(None, 1) == "10.0.0.2"


def _cron_headers(secret: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret}"}


def test_cron_endpoints_are_off_without_a_secret_and_protected_with_one(
    client: TestClient, app: FastAPI, settings: Settings
) -> None:
    url = "/api/v1/internal/cron/run-jobs"
    assert client.get(url).status_code == 404  # no CRON_SECRET configured: they don't exist

    app.state.settings = settings.model_copy(
        update={"cron_secret": SecretStr("s3cret-s3cret-s3cret")}
    )
    assert client.get(url).status_code == 401
    assert client.get(url, headers=_cron_headers("wrong")).status_code == 401
    assert client.get(url, headers={"Authorization": "s3cret-s3cret-s3cret"}).status_code == 401
    ok = client.get(url, headers=_cron_headers("s3cret-s3cret-s3cret"))
    assert ok.status_code == 200 and ok.headers["cache-control"] == "no-store"
    assert set(ok.json()) == {"checked", "paid", "expired", "review", "errors"}
    prices = client.get(
        "/api/v1/internal/cron/refresh-prices", headers=_cron_headers("s3cret-s3cret-s3cret")
    )
    assert prices.status_code == 200 and prices.json() == {"ok": True}
    # They are not part of the public API contract.
    assert not any("/internal/" in path for path in client.get("/api/openapi.json").json()["paths"])


def test_cron_run_expires_an_overdue_pending_order(
    client: TestClient, app: FastAPI, settings: Settings, db: Session
) -> None:
    from sqlalchemy import select, update

    from app.core.time import utcnow
    from app.models import Order
    from tests.api.order_helpers import add_to_cart, place_order

    add_to_cart(client, db, "ANV-RG-002-12")
    reference = place_order(client).json()["order"]["reference"]
    db.execute(
        update(Order)
        .where(Order.reference == reference)
        .values(payment_expires_at=utcnow() - timedelta(minutes=5))
    )
    db.commit()
    app.state.settings = settings.model_copy(
        update={"cron_secret": SecretStr("s3cret-s3cret-s3cret")}
    )
    done = client.get(
        "/api/v1/internal/cron/run-jobs", headers=_cron_headers("s3cret-s3cret-s3cret")
    )
    assert done.status_code == 200 and done.json()["expired"] == 1
    assert db.scalar(select(Order.status).where(Order.reference == reference)) == "expired"


def test_the_job_loop_is_skipped_on_vercel_and_when_disabled(settings: Settings) -> None:
    from app.jobs import job_loop_enabled

    on = settings.model_copy(update={"background_jobs_enabled": True})
    off = settings.model_copy(update={"background_jobs_enabled": False})
    assert job_loop_enabled(on, {}) is True
    assert job_loop_enabled(on, {"VERCEL": "1"}) is False
    assert job_loop_enabled(off, {}) is False


def test_engine_can_turn_off_server_side_prepared_statements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import db as db_module

    captured: list[dict[str, object]] = []
    monkeypatch.setattr(
        db_module, "create_engine", lambda url, **kwargs: captured.append(kwargs["connect_args"])
    )
    url = "postgresql+psycopg://u:p@127.0.0.1:5/x"
    db_module.make_engine(url, pool_size=1, max_overflow=0, prepare_statements=False)
    db_module.make_engine(url)
    assert captured[0] == {"options": "-c timezone=UTC", "prepare_threshold": None}
    assert captured[1] == {"options": "-c timezone=UTC"}
