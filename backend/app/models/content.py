"""Editable content pages, newsletter subscribers and contact enquiries."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UUIDPrimaryKey, enum_check
from app.models.enums import ENQUIRY_STATUSES, SUBSCRIBER_STATUSES


class ContentPage(UUIDPrimaryKey, Timestamps, Base):
    """About, FAQ, guides and policy pages (Markdown, rendered without raw HTML)."""

    __tablename__ = "content_pages"

    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(300))
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # True while the text is a template awaiting the owner's (and, for policies, a lawyer's) review.
    is_draft_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class NewsletterSubscriber(UUIDPrimaryKey, Base):
    __tablename__ = "newsletter_subscribers"
    __table_args__ = (CheckConstraint(enum_check("status", SUBSCRIBER_STATUSES), name="status"),)

    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="subscribed")
    source: Mapped[str | None] = mapped_column(String(40))
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unsubscribe_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ContactEnquiry(UUIDPrimaryKey, Base):
    __tablename__ = "contact_enquiries"
    __table_args__ = (
        CheckConstraint(enum_check("status", ENQUIRY_STATUSES), name="status"),
        Index("ix_contact_enquiries_status_created", "status", "created_at"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
