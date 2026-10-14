"""Fixed-window rate limiting stored in PostgreSQL, so limits hold across workers and restarts.

The counter update is committed immediately (in its own small transaction) so that a request which
later fails — e.g. a wrong password — still counts against the limit.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.client_ip import client_ip
from app.core.db import get_db
from app.core.errors import RateLimited
from app.core.time import utcnow

_UPSERT = text(
    """
    INSERT INTO rate_limit_buckets (key, window_start, count)
    VALUES (:key, :now, 1)
    ON CONFLICT (key) DO UPDATE SET
        count = CASE WHEN rate_limit_buckets.window_start <= :cutoff THEN 1
                     ELSE rate_limit_buckets.count + 1 END,
        window_start = CASE WHEN rate_limit_buckets.window_start <= :cutoff THEN :now
                            ELSE rate_limit_buckets.window_start END
    RETURNING count, window_start
    """
)


def _bucket_key(scope: str, identity: str) -> str:
    # Hash identities (IPs, emails) so the table holds no personal data in clear text.
    digest = hashlib.sha256(identity.lower().encode()).hexdigest()[:32]
    return f"{scope}:{digest}"


def hit(
    db: Session, scope: str, identity: str, *, limit: int, window_seconds: int, enabled: bool = True
) -> None:
    """Count one attempt; raise RateLimited (429 + Retry-After) once `limit` is exceeded."""
    if not enabled:
        return
    now = utcnow()
    row = db.execute(
        _UPSERT,
        {
            "key": _bucket_key(scope, identity),
            "now": now,
            "cutoff": now - timedelta(seconds=window_seconds),
        },
    ).one()
    db.commit()
    count, window_start = row
    if count > limit:
        retry_after = max(
            1, int((window_start + timedelta(seconds=window_seconds) - now).total_seconds())
        )
        raise RateLimited(headers={"Retry-After": str(retry_after)})


def rate_limit(scope: str, *, limit: int, window_seconds: int) -> Callable[..., None]:
    """FastAPI dependency limiting requests per client IP for one endpoint group."""

    def dependency(request: Request, db: Session = Depends(get_db)) -> None:
        hit(
            db,
            scope,
            client_ip(request),
            limit=limit,
            window_seconds=window_seconds,
            enabled=request.app.state.settings.rate_limit_enabled,
        )

    return dependency


def purge_expired(db: Session, older_than_seconds: int = 86_400) -> int:
    """Housekeeping: delete buckets whose window ended long ago. Caller commits."""
    result = db.execute(
        text("DELETE FROM rate_limit_buckets WHERE window_start < :cutoff"),
        {"cutoff": utcnow() - timedelta(seconds=older_than_seconds)},
    )
    return int(getattr(result, "rowcount", 0) or 0)
