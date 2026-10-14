"""Helpers for setting and clearing the app's cookies with consistent security flags.

Cookie design: docs/architecture/AUTHENTICATION.md §2.
"""

from __future__ import annotations

import secrets
from typing import Literal

from fastapi import Response

from app.core.config import Settings
from app.core.middleware import CSRF_COOKIE


def set_cookie(
    response: Response,
    settings: Settings,
    name: str,
    value: str,
    *,
    max_age: int | None,
    httponly: bool = True,
    samesite: Literal["lax", "strict"] = "lax",
    path: str = "/",
) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=httponly,
        secure=settings.cookie_secure,
        samesite=samesite,
        path=path,
        domain=settings.cookie_domain or None,
    )


def clear_cookie(response: Response, settings: Settings, name: str, *, path: str = "/") -> None:
    response.delete_cookie(
        key=name,
        path=path,
        domain=settings.cookie_domain or None,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def issue_csrf_cookie(response: Response, settings: Settings) -> str:
    """Set a fresh CSRF token cookie (readable by JavaScript, by design) and return it."""
    token = secrets.token_urlsafe(32)
    set_cookie(
        response, settings, CSRF_COOKIE, token, max_age=None, httponly=False, samesite="strict"
    )
    return token
