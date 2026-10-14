"""Append-only audit log for sensitive actions (admin changes, role changes, rate changes…)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import redact
from app.models import AuditLog, User


def record(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str | None = None,
    changes: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Add an audit entry in the caller's transaction. Secrets in `changes` are redacted."""
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_role=actor.role if actor else "system",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        changes=redact(changes or {}),
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
