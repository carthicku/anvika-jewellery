"""Time helpers: the app works in UTC everywhere; the frontend localises for display."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)
