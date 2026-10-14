"""Pure-ASGI middleware: request context + access log, security headers, body size limit, CSRF.

Pure ASGI (rather than BaseHTTPMiddleware) keeps streaming bodies and context variables intact.
Order in app.main (outermost first): RequestContext → SecurityHeaders → BodySizeLimit → CSRF.
"""

from __future__ import annotations

import hmac
import json
import logging
import re
import time
import uuid
from collections.abc import Iterable
from http.cookies import SimpleCookie
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_body
from app.core.request_context import set_request_id, set_user_id

access_logger = logging.getLogger("app.access")

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = b"x-csrf-token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return str(value.decode("latin-1"))
    return None


def _cookie(scope: Scope, name: str) -> str | None:
    raw = _header(scope, b"cookie")
    if not raw:
        return None
    jar: SimpleCookie = SimpleCookie()
    try:
        jar.load(raw)
    except Exception:  # malformed cookie header
        return None
    morsel = jar.get(name)
    return morsel.value if morsel else None


async def _send_json(send: Send, status: int, body: dict[str, Any]) -> None:
    payload = json.dumps(body).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})


class RequestContextMiddleware:
    """Assigns a request id, exposes it as X-Request-ID, and writes one access-log line."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = _header(scope, b"x-request-id")
        request_id = incoming if incoming and _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        set_request_id(request_id)
        set_user_id(None)
        scope.setdefault("state", {})
        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            state = scope.get("state", {})
            access_logger.info(
                "request",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),  # path only: query strings may hold personal data
                    "status": status_holder["status"],
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "uid": state.get("user_id"),
                },
            )


class SecurityHeadersMiddleware:
    """Adds defensive headers to every response. The SPA's own CSP is set by the web server."""

    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_docs = scope.get("path", "").startswith("/api/docs") or scope.get("path", "") in (
            "/api/openapi.json",
        )

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {k.lower() for k, _ in headers}
                extra: list[tuple[bytes, bytes]] = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (b"cross-origin-resource-policy", b"same-origin"),
                ]
                if not is_docs:
                    # API responses are data, never documents: forbid everything.
                    extra.append(
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'")
                    )
                if self.hsts:
                    extra.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                headers.extend((k, v) for k, v in extra if k not in existing)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodySizeLimitMiddleware:
    """Rejects request bodies above a limit (larger limit for admin image uploads)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        default_limit: int = 1_000_000,
        upload_limit: int = 10_500_000,
        upload_path_pattern: str = r"^/api/v1/admin/products/[^/]+/images$",
    ) -> None:
        self.app = app
        self.default_limit = default_limit
        self.upload_limit = upload_limit
        self.upload_re = re.compile(upload_path_pattern)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = (
            self.upload_limit if self.upload_re.match(scope.get("path", "")) else self.default_limit
        )
        declared = _header(scope, b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await _send_json(
                send, 413, error_body("PAYLOAD_TOO_LARGE", "The request is too large.")
            )
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _BodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _BodyTooLarge:
            await _send_json(
                send, 413, error_body("PAYLOAD_TOO_LARGE", "The request is too large.")
            )


class _BodyTooLarge(Exception):
    pass


class CSRFMiddleware:
    """Double-submit CSRF protection for cookie-authenticated, state-changing API requests.

    Unsafe requests must send an X-CSRF-Token header equal to the csrf_token cookie, and if they
    carry an Origin header it must be an allowed origin. Webhooks are exempt (HMAC-authenticated).
    See docs/architecture/AUTHENTICATION.md §2.
    """

    def __init__(
        self, app: ASGIApp, *, allowed_origins: Iterable[str], exempt_prefixes: Iterable[str]
    ) -> None:
        self.app = app
        self.allowed_origins = {o.rstrip("/") for o in allowed_origins}
        self.exempt_prefixes = tuple(exempt_prefixes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") not in UNSAFE_METHODS
            or not scope.get("path", "").startswith("/api/")
            or scope.get("path", "").startswith(self.exempt_prefixes)
        ):
            await self.app(scope, receive, send)
            return

        origin = _header(scope, b"origin")
        if origin and origin.rstrip("/") not in self.allowed_origins:
            await _send_json(send, 403, error_body("CSRF_FAILED", "Request origin is not allowed."))
            return

        cookie_token = _cookie(scope, CSRF_COOKIE)
        header_token = _header(scope, CSRF_HEADER)
        if (
            not cookie_token
            or not header_token
            or not hmac.compare_digest(cookie_token.encode(), header_token.encode())
        ):
            await _send_json(
                send,
                403,
                error_body(
                    "CSRF_FAILED", "Your session security token is missing or expired. Reload."
                ),
            )
            return
        await self.app(scope, receive, send)
