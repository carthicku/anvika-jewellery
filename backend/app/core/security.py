"""Password hashing, opaque tokens and access JWTs. See docs/architecture/AUTHENTICATION.md."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings

# Argon2id with the library's current recommended parameters.
_hasher = PasswordHasher()
# Verified against when the email is unknown, so "no such user" takes as long as "wrong password".
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")

PASSWORD_MIN = 10
PASSWORD_MAX = 128
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - a claim value, not a secret


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> tuple[bool, bool]:
    """Return (matches, needs_rehash). Always does the full amount of work."""
    try:
        _hasher.verify(password_hash or _DUMMY_HASH, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False
    if password_hash is None:
        return False, False
    return True, _hasher.check_needs_rehash(password_hash)


def password_problems(password: str, email: str | None = None) -> list[str]:
    """Human-readable reasons a password is not acceptable (empty list = acceptable)."""
    problems = []
    if len(password) < PASSWORD_MIN:
        problems.append(f"Use at least {PASSWORD_MIN} characters.")
    if len(password) > PASSWORD_MAX:
        problems.append(f"Use at most {PASSWORD_MAX} characters.")
    if password.isdigit():
        problems.append("Don't use only numbers.")
    if email and password.strip().lower() == email.strip().lower():
        problems.append("Don't use your email address as your password.")
    if len(set(password)) < 4:
        problems.append("Use a less repetitive password.")
    return problems


def new_token() -> str:
    """256-bit URL-safe random token (sent to the user; never stored in clear)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID
    expires_at: datetime


class AccessTokenExpired(Exception):
    pass


class AccessTokenInvalid(Exception):
    pass


def create_access_token(
    settings: Settings, *, user_id: uuid.UUID, session_id: uuid.UUID, now: datetime | None = None
) -> tuple[str, datetime]:
    issued = now or datetime.now(UTC)
    expires = issued + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=JWT_ALGORITHM)
    return token, expires


def decode_access_token(settings: Settings, token: str) -> AccessClaims:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],  # never accept "none" or other algorithms
            options={"require": ["exp", "iat", "sub", "sid", "typ"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AccessTokenExpired from exc
    except jwt.PyJWTError as exc:
        raise AccessTokenInvalid from exc
    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise AccessTokenInvalid
    try:
        return AccessClaims(
            user_id=uuid.UUID(payload["sub"]),
            session_id=uuid.UUID(payload["sid"]),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (ValueError, KeyError) as exc:
        raise AccessTokenInvalid from exc
