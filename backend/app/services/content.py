"""Content pages, public store settings, contact enquiries and newsletter subscriptions."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import BadRequest, NotFound
from app.core.time import utcnow
from app.models import ContactEnquiry, ContentPage, NewsletterSubscriber
from app.schemas.common import StrictIn
from app.services import store_settings

MIN_FORM_SECONDS = 2  # humans take longer than this to fill a form; many bots don't


class ContentPageOut(BaseModel):
    slug: str
    title: str
    summary: str | None
    body_markdown: str
    is_draft_template: bool
    updated_at: datetime


class AnnouncementOut(BaseModel):
    enabled: bool
    text: str
    link: str | None


class PublicSettingsOut(BaseModel):
    store_name: str
    tagline: str
    support_email: str
    support_phone: str
    whatsapp: str | None
    business_address: str
    business_hours: str
    announcement: AnnouncementOut
    payment_mode: Literal["razorpay", "simulator"]
    email_verification_required: bool


def get_page(db: Session, slug: str) -> ContentPageOut:
    page = db.scalar(select(ContentPage).where(ContentPage.slug == slug))
    if page is None:
        raise NotFound("We couldn't find that page.")
    return ContentPageOut(
        slug=page.slug,
        title=page.title,
        summary=page.summary,
        body_markdown=page.body_markdown,
        is_draft_template=page.is_draft_template,
        updated_at=page.updated_at,
    )


def public_settings(db: Session, settings: Settings) -> PublicSettingsOut:
    store = store_settings.get_group(db, "store")
    announcement = store_settings.get_group(db, "announcement")
    return PublicSettingsOut(
        store_name=settings.store_name,
        tagline=store["tagline"],
        support_email=store["support_email"],
        support_phone=store["support_phone"],
        whatsapp=store["whatsapp"],
        business_address=store["business_address"],
        business_hours=store["business_hours"],
        announcement=AnnouncementOut(**announcement),
        payment_mode=settings.payment_provider,
        email_verification_required=settings.email_verification_required,
    )


# --------------------------------------------------------------------------------------------
# Contact form
# --------------------------------------------------------------------------------------------


class ContactIn(StrictIn):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    subject: str = Field(min_length=2, max_length=160)
    message: str = Field(min_length=10, max_length=5000)
    # Anti-spam: `website` is a hidden field humans never fill; `elapsed_seconds` is the time the
    # form was open. Failing requests get the normal success response but are dropped.
    website: str = Field(default="", max_length=200)
    elapsed_seconds: int = Field(default=0, ge=0, le=86_400)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        digits = value.replace(" ", "").replace("-", "")
        if not digits.lstrip("+").isdigit() or not 7 <= len(digits.lstrip("+")) <= 15:
            raise ValueError("Enter a valid phone number.")
        return digits


def looks_automated(website: str, elapsed_seconds: int) -> bool:
    return bool(website) or elapsed_seconds < MIN_FORM_SECONDS


def submit_contact(db: Session, data: ContactIn) -> None:
    if looks_automated(data.website, data.elapsed_seconds):
        return
    db.add(
        ContactEnquiry(
            name=data.name,
            email=str(data.email).lower(),
            phone=data.phone,
            subject=data.subject,
            message=data.message,
        )
    )


# --------------------------------------------------------------------------------------------
# Newsletter
# --------------------------------------------------------------------------------------------


class NewsletterSubscribeIn(StrictIn):
    email: EmailStr
    consent: bool
    source: str = Field(default="footer", max_length=40)
    website: str = Field(default="", max_length=200)
    elapsed_seconds: int = Field(default=10, ge=0, le=86_400)


class NewsletterUnsubscribeIn(StrictIn):
    token: str = Field(min_length=16, max_length=128)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def subscribe(db: Session, data: NewsletterSubscribeIn) -> None:
    """Idempotent. The response never reveals whether the address was already subscribed."""
    if not data.consent:
        raise BadRequest(
            "Please confirm you would like to receive our emails.", code="CONSENT_REQUIRED"
        )
    if looks_automated(data.website, data.elapsed_seconds):
        return
    email = str(data.email).lower()
    existing = db.scalar(select(NewsletterSubscriber).where(NewsletterSubscriber.email == email))
    now = utcnow()
    if existing is None:
        db.add(
            NewsletterSubscriber(
                email=email,
                status="subscribed",
                source=data.source,
                consent_at=now,
                unsubscribe_token_hash=_hash(secrets.token_urlsafe(32)),
            )
        )
    elif existing.status == "unsubscribed":
        existing.status = "subscribed"
        existing.consent_at = now
        existing.unsubscribed_at = None


def unsubscribe(db: Session, data: NewsletterUnsubscribeIn) -> None:
    subscriber = db.scalar(
        select(NewsletterSubscriber).where(
            NewsletterSubscriber.unsubscribe_token_hash == _hash(data.token)
        )
    )
    if subscriber is None:
        raise NotFound("This unsubscribe link is not valid.")
    subscriber.status = "unsubscribed"
    subscriber.unsubscribed_at = utcnow()
