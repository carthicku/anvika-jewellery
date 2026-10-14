"""Public store information, content pages, contact form, newsletter and PIN-code checks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings
from app.core.config import Settings
from app.core.db import get_db
from app.core.rate_limit import rate_limit
from app.schemas.common import OkOut
from app.services import content, shipping
from app.services.content import (
    ContactIn,
    ContentPageOut,
    NewsletterSubscribeIn,
    NewsletterUnsubscribeIn,
    PublicSettingsOut,
)
from app.services.shipping import PincodeCheckOut

router = APIRouter(tags=["content"])


@router.get("/settings/public", response_model=PublicSettingsOut)
def public_settings(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> PublicSettingsOut:
    response.headers["Cache-Control"] = "public, max-age=60"
    return content.public_settings(db, settings)


@router.get("/content/{slug}", response_model=ContentPageOut)
def content_page(slug: str, response: Response, db: Session = Depends(get_db)) -> ContentPageOut:
    response.headers["Cache-Control"] = "public, max-age=300"
    return content.get_page(db, slug)


@router.get(
    "/shipping/pincode/{pincode}",
    response_model=PincodeCheckOut,
    dependencies=[Depends(rate_limit("pincode", limit=60, window_seconds=60))],
)
def pincode_check(pincode: str, db: Session = Depends(get_db)) -> PincodeCheckOut:
    return shipping.check_pincode(db, pincode)


@router.post(
    "/contact",
    response_model=OkOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("contact", limit=5, window_seconds=3600))],
)
def contact(data: ContactIn, db: Session = Depends(get_db)) -> OkOut:
    content.submit_contact(db, data)
    db.commit()
    return OkOut(message="Thank you — we have received your message and will reply soon.")


@router.post(
    "/newsletter/subscribe",
    response_model=OkOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("newsletter", limit=5, window_seconds=3600))],
)
def newsletter_subscribe(data: NewsletterSubscribeIn, db: Session = Depends(get_db)) -> OkOut:
    content.subscribe(db, data)
    db.commit()
    return OkOut(message="Thank you for subscribing.")


@router.post(
    "/newsletter/unsubscribe",
    response_model=OkOut,
    dependencies=[Depends(rate_limit("newsletter-unsub", limit=10, window_seconds=3600))],
)
def newsletter_unsubscribe(data: NewsletterUnsubscribeIn, db: Session = Depends(get_db)) -> OkOut:
    content.unsubscribe(db, data)
    db.commit()
    return OkOut(message="You have been unsubscribed.")
