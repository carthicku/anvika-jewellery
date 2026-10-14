"""Accounts and sessions. Design: docs/architecture/AUTHENTICATION.md and ADR-0003.

Routes call these functions and then commit. Functions that must persist something even when they
end in an error (e.g. revoking a session after refresh-token reuse) commit explicitly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, BadRequest, Conflict, NotAuthenticated, ValidationFailed
from app.core.rate_limit import hit
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_token,
    password_problems,
    verify_password,
)
from app.core.time import utcnow
from app.models import User, UserSession, UserToken
from app.services import email as email_service

ABSOLUTE_SESSION_DAYS = 90
RESET_TOKEN_MINUTES = 30
VERIFY_TOKEN_HOURS = 48
REFRESH_RACE_SECONDS = 20


class InvalidCredentials(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "The email or password is incorrect."


@dataclass(frozen=True)
class RequestMeta:
    ip: str | None
    user_agent: str | None


@dataclass(frozen=True)
class IssuedSession:
    session: UserSession
    refresh_token: str
    access_token: str
    access_expires_at: datetime


def normalise_email(email: str) -> str:
    return email.strip().lower()


def _check_password(password: str, email: str | None, field: str = "password") -> None:
    problems = password_problems(password, email)
    if problems:
        raise ValidationFailed({field: " ".join(problems)})


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalise_email(email)))


# --------------------------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------------------------


def create_session(db: Session, settings: Settings, user: User, meta: RequestMeta) -> IssuedSession:
    now = utcnow()
    refresh = new_token()
    session = UserSession(
        id=uuid.uuid4(),
        user_id=user.id,
        refresh_token_hash=hash_token(refresh),
        user_agent=(meta.user_agent or "")[:300] or None,
        ip_address=meta.ip,
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
        absolute_expires_at=now + timedelta(days=ABSOLUTE_SESSION_DAYS),
    )
    db.add(session)
    db.flush()
    access, expires = create_access_token(settings, user_id=user.id, session_id=session.id, now=now)
    return IssuedSession(session, refresh, access, expires)


def refresh_session(db: Session, settings: Settings, refresh_token: str) -> IssuedSession:
    """Rotate the refresh token. Presenting an already-rotated token revokes the session."""
    now = utcnow()
    token_hash = hash_token(refresh_token)
    session = db.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == token_hash).with_for_update()
    )
    if session is None:
        stale = db.scalar(
            select(UserSession)
            .where(
                UserSession.previous_refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
            .with_for_update()
        )
        if stale is not None:
            if (now - stale.last_used_at).total_seconds() < REFRESH_RACE_SECONDS:
                # Two tabs refreshed at the same moment; the other one already rotated the token.
                raise Conflict("Session was just refreshed. Please retry.", code="REFRESH_RACE")
            # An old token was replayed: assume it was stolen and end the session.
            stale.revoked_at = now
            stale.revoked_reason = "refresh_token_reuse"
            db.commit()
        raise NotAuthenticated("Your session has ended. Please sign in again.")

    user = session.user
    if (
        session.revoked_at is not None
        or session.expires_at <= now
        or session.absolute_expires_at <= now
        or not user.is_active
    ):
        raise NotAuthenticated("Your session has ended. Please sign in again.")

    new_refresh = new_token()
    session.previous_refresh_token_hash = session.refresh_token_hash
    session.refresh_token_hash = hash_token(new_refresh)
    session.last_used_at = now
    session.expires_at = min(
        now + timedelta(days=settings.refresh_token_ttl_days), session.absolute_expires_at
    )
    access, expires = create_access_token(settings, user_id=user.id, session_id=session.id, now=now)
    return IssuedSession(session, new_refresh, access, expires)


def revoke_session(session: UserSession, reason: str) -> None:
    if session.revoked_at is None:
        session.revoked_at = utcnow()
        session.revoked_reason = reason


def revoke_all_sessions(
    db: Session, user_id: uuid.UUID, reason: str, except_session_id: uuid.UUID | None = None
) -> None:
    stmt = update(UserSession).where(
        UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
    )
    if except_session_id is not None:
        stmt = stmt.where(UserSession.id != except_session_id)
    db.execute(stmt.values(revoked_at=utcnow(), revoked_reason=reason))


def active_sessions(db: Session, user_id: uuid.UUID) -> list[UserSession]:
    return list(
        db.scalars(
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > utcnow(),
            )
            .order_by(UserSession.last_used_at.desc())
        ).all()
    )


# --------------------------------------------------------------------------------------------
# Registration and login
# --------------------------------------------------------------------------------------------


def register(
    db: Session,
    settings: Settings,
    *,
    full_name: str,
    email: str,
    password: str,
    phone: str | None,
    meta: RequestMeta,
) -> tuple[User, IssuedSession]:
    address = normalise_email(email)
    _check_password(password, address)
    if get_user_by_email(db, address) is not None:
        raise Conflict(
            "An account with this email already exists. Sign in or reset your password.",
            code="EMAIL_IN_USE",
        )
    user = User(
        email=address,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        phone=phone,
        role="customer",
        last_login_at=utcnow(),
    )
    db.add(user)
    db.flush()
    send_verification_email(db, settings, user)
    return user, create_session(db, settings, user, meta)


def login(
    db: Session, settings: Settings, *, email: str, password: str, meta: RequestMeta
) -> tuple[User, IssuedSession]:
    address = normalise_email(email)
    # Per-account limit (per-IP limits are applied by the route) slows down password guessing.
    hit(
        db,
        "login-email",
        address,
        limit=10,
        window_seconds=900,
        enabled=settings.rate_limit_enabled,
    )
    user = get_user_by_email(db, address)
    matches, needs_rehash = verify_password(password, user.password_hash if user else None)
    if user is None or not matches or not user.is_active:
        raise InvalidCredentials()
    if needs_rehash:
        user.password_hash = hash_password(password)
    user.last_login_at = utcnow()
    return user, create_session(db, settings, user, meta)


# --------------------------------------------------------------------------------------------
# Tokens: email verification and password reset
# --------------------------------------------------------------------------------------------


def _issue_token(
    db: Session, user: User, purpose: str, lifetime: timedelta
) -> tuple[str, UserToken]:
    # Only the newest token of each purpose stays valid.
    db.execute(
        update(UserToken)
        .where(
            UserToken.user_id == user.id, UserToken.purpose == purpose, UserToken.used_at.is_(None)
        )
        .values(used_at=utcnow())
    )
    token = new_token()
    row = UserToken(
        id=uuid.uuid4(),
        user_id=user.id,
        purpose=purpose,
        token_hash=hash_token(token),
        expires_at=utcnow() + lifetime,
    )
    db.add(row)
    db.flush()
    return token, row


def _consume_token(db: Session, token: str, purpose: str) -> UserToken:
    row = db.scalar(
        select(UserToken)
        .where(
            UserToken.token_hash == hash_token(token),
            UserToken.purpose == purpose,
            UserToken.used_at.is_(None),
            UserToken.expires_at > utcnow(),
        )
        .with_for_update()
    )
    if row is None:
        raise BadRequest(
            "This link is invalid or has expired. Please request a new one.", code="INVALID_TOKEN"
        )
    row.used_at = utcnow()
    return row


def send_verification_email(db: Session, settings: Settings, user: User) -> None:
    if user.email_verified_at is not None:
        return
    token, row = _issue_token(db, user, "email_verify", timedelta(hours=VERIFY_TOKEN_HOURS))
    email_service.enqueue(
        db,
        key=f"verify_email:{row.id}",
        to=user.email,
        template="verify_email",
        subject=f"Confirm your email for {settings.store_name}",
        context={
            "name": user.full_name,
            "verify_url": f"{settings.public_site_url}/verify-email?token={token}",
        },
    )


def verify_email(db: Session, token: str) -> User:
    row = _consume_token(db, token, "email_verify")
    user = db.get(User, row.user_id)
    if user is None:  # cannot happen: foreign key with ON DELETE CASCADE
        raise BadRequest("This link is invalid or has expired.", code="INVALID_TOKEN")
    user.email_verified_at = user.email_verified_at or utcnow()
    return user


def request_password_reset(db: Session, settings: Settings, email: str) -> None:
    """Always succeeds silently, so responses never reveal whether an account exists."""
    address = normalise_email(email)
    hit(
        db,
        "forgot-email",
        address,
        limit=3,
        window_seconds=3600,
        enabled=settings.rate_limit_enabled,
    )
    user = get_user_by_email(db, address)
    if user is None or not user.is_active:
        return
    token, row = _issue_token(db, user, "password_reset", timedelta(minutes=RESET_TOKEN_MINUTES))
    email_service.enqueue(
        db,
        key=f"password_reset:{row.id}",
        to=user.email,
        template="password_reset",
        subject=f"Reset your {settings.store_name} password",
        context={
            "name": user.full_name,
            "reset_url": f"{settings.public_site_url}/reset-password?token={token}",
        },
    )


def _notify_password_changed(db: Session, settings: Settings, user: User) -> None:
    email_service.enqueue(
        db,
        key=f"password_changed:{user.id}:{int(utcnow().timestamp())}",
        to=user.email,
        template="password_changed",
        subject=f"Your {settings.store_name} password was changed",
        context={"name": user.full_name},
    )


def reset_password(db: Session, settings: Settings, token: str, new_password: str) -> User:
    row = _consume_token(db, token, "password_reset")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise BadRequest("This link is invalid or has expired.", code="INVALID_TOKEN")
    _check_password(new_password, user.email)
    user.password_hash = hash_password(new_password)
    # A reset proves control of the inbox: treat the email as verified, end every session.
    user.email_verified_at = user.email_verified_at or utcnow()
    revoke_all_sessions(db, user.id, "password_reset")
    _notify_password_changed(db, settings, user)
    return user


def change_password(
    db: Session,
    settings: Settings,
    user: User,
    current_session_id: uuid.UUID,
    current_password: str,
    new_password: str,
) -> None:
    matches, _ = verify_password(current_password, user.password_hash)
    if not matches:
        raise ValidationFailed({"current_password": "Your current password is incorrect."})
    _check_password(new_password, user.email, field="new_password")
    user.password_hash = hash_password(new_password)
    revoke_all_sessions(db, user.id, "password_changed", except_session_id=current_session_id)
    _notify_password_changed(db, settings, user)
