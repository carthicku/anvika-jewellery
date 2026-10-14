"""Transactional email outbox (ADR-0008): rows are written in the business transaction and sent
after commit by the dispatcher, exactly once per idempotency key."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey, enum_check

EMAIL_STATUSES = ("pending", "sent", "written_to_sink", "failed")


class EmailOutbox(UUIDPrimaryKey, Base):
    __tablename__ = "email_outbox"
    __table_args__ = (
        CheckConstraint(enum_check("status", EMAIL_STATUSES), name="status"),
        Index("ix_email_outbox_status_next", "status", "next_attempt_at"),
    )

    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    to_email: Mapped[str] = mapped_column(String(254), nullable=False)
    template: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    # Template variables. Cleared after sending because they may contain one-time links.
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
