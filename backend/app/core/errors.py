"""Application errors and the single JSON error format used by every endpoint.

Services raise `AppError` subclasses; the handlers below turn them (and framework errors) into:

    {"error": {"code": "...", "message": "...", "details": {...}, "request_id": "..."}}

See docs/architecture/API_CONTRACT.md ("Errors").
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import get_request_id

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """Base class for expected, user-facing errors."""

    status_code: int = 400
    code: str = "BAD_REQUEST"
    message: str = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        self.headers = headers
        super().__init__(self.message)


class BadRequest(AppError):
    pass


class NotAuthenticated(AppError):
    status_code = 401
    code = "NOT_AUTHENTICATED"
    message = "Please sign in to continue."


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to do that."


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "We couldn't find what you were looking for."


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "That action conflicts with the current state."


class OutOfStock(Conflict):
    code = "OUT_OF_STOCK"
    message = "Some items are no longer available in the requested quantity."


class PriceChanged(Conflict):
    code = "PRICE_CHANGED"
    message = "Some prices have changed. Please review the updated total."


class InvalidStateTransition(Conflict):
    code = "INVALID_STATE_TRANSITION"
    message = "That change is not allowed for the current status."


class ValidationFailed(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "Please check the highlighted fields."

    def __init__(self, fields: dict[str, str], message: str | None = None) -> None:
        super().__init__(message, details={"fields": fields})


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Too many attempts. Please wait a moment and try again."


class PayloadTooLarge(AppError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"
    message = "The request is too large."


class ServiceUnavailable(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "This service is temporarily unavailable. Please try again shortly."


class PaymentProviderError(AppError):
    status_code = 502
    code = "PAYMENT_PROVIDER_ERROR"
    message = "The payment provider could not be reached. Please try again."


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": get_request_id(),
        }
    }


def _field_path(loc: tuple[Any, ...]) -> str:
    # Drop the leading "body"/"query"/"path" segment so fields match form field names.
    parts = [str(p) for p in loc[1:]] if len(loc) > 1 else [str(p) for p in loc]
    return ".".join(parts)


def _clean_message(raw: str) -> str:
    # Pydantic prefixes custom ValueError messages with "Value error, ".
    return raw.removeprefix("Value error, ")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            error_body(exc.code, exc.message, exc.details),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for err in exc.errors():
            path = _field_path(tuple(err.get("loc", ())))
            fields.setdefault(path or "body", _clean_message(str(err.get("msg", "Invalid value"))))
        return JSONResponse(
            error_body(ValidationFailed.code, ValidationFailed.message, {"fields": fields}),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {
            400: "BAD_REQUEST",
            401: "NOT_AUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            413: "PAYLOAD_TOO_LARGE",
            429: "RATE_LIMITED",
        }
        code = codes.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        if exc.status_code == 404:
            message = NotFound.message
        return JSONResponse(
            error_body(code, message), status_code=exc.status_code, headers=exc.headers
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Full details go to the log (correlated by request id), never to the client.
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            error_body("INTERNAL_ERROR", "Something went wrong on our side. Please try again."),
            status_code=500,
        )
