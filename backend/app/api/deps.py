"""Shared FastAPI dependencies: settings, request metadata, authentication and permissions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.client_ip import client_ip
from app.core.config import Settings
from app.core.cookies import ACCESS_COOKIE
from app.core.db import get_db
from app.core.errors import AppError, Forbidden, NotAuthenticated
from app.core.permissions import Permission, has_permission
from app.core.request_context import set_user_id
from app.core.security import AccessTokenExpired, AccessTokenInvalid, decode_access_token
from app.core.time import utcnow
from app.models import User, UserSession
from app.services.auth import RequestMeta


class SessionExpired(AppError):
    """Access token expired: the browser should call /auth/refresh and retry (ADR-0003)."""

    status_code = 401
    code = "SESSION_EXPIRED"
    message = "Your session needs refreshing."


def get_app_settings(request: Request) -> Settings:
    """Settings of the running app (tests create apps with their own settings)."""
    settings: Settings = request.app.state.settings
    return settings


def get_request_meta(request: Request) -> RequestMeta:
    return RequestMeta(ip=client_ip(request), user_agent=request.headers.get("user-agent"))


@dataclass(frozen=True)
class Auth:
    user: User
    session: UserSession


def get_optional_auth(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Auth | None:
    """The signed-in user, or None for guests. An EXPIRED token raises SESSION_EXPIRED so the
    browser refreshes; a missing, malformed or revoked one means "guest"."""
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    try:
        claims = decode_access_token(settings, token)
    except AccessTokenExpired as exc:
        raise SessionExpired() from exc
    except AccessTokenInvalid:
        return None
    session = db.get(UserSession, claims.session_id)
    if (
        session is None
        or session.user_id != claims.user_id
        or session.revoked_at is not None
        or session.expires_at <= utcnow()
    ):
        return None
    user = session.user
    if not user.is_active:
        return None
    request.state.user_id = str(user.id)  # for the access log
    set_user_id(str(user.id))
    return Auth(user=user, session=session)


def get_auth(auth: Auth | None = Depends(get_optional_auth)) -> Auth:
    if auth is None:
        raise NotAuthenticated()
    return auth


def get_current_user(auth: Auth = Depends(get_auth)) -> User:
    return auth.user


def require_permission(permission: Permission) -> Callable[..., User]:
    """Dependency factory for admin endpoints. The role always comes from the database row."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise Forbidden()
        return user

    dependency.required_permission = permission  # type: ignore[attr-defined]  # read by tests
    return dependency
