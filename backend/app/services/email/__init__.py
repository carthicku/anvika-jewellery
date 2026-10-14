"""Transactional email: idempotent outbox + dispatcher + pluggable senders (ADR-0008).

Business code calls `enqueue(...)` inside its transaction. After commit, `dispatch_pending(...)`
renders and sends. Statuses never overstate delivery: the development file sink records
`written_to_sink`, only a successful SMTP hand-off records `sent`.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from collections.abc import Callable
from datetime import timedelta
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.time import utcnow
from app.models import EmailOutbox
from app.services.email.templates import render

logger = logging.getLogger("app.email")

MAX_ATTEMPTS = 5
# In-memory "sent" messages for EMAIL_BACKEND=memory (automated tests only).
MEMORY_OUTBOX: list[EmailMessage] = []


def enqueue(
    db: Session,
    *,
    key: str,
    to: str,
    template: str,
    subject: str,
    context: dict[str, Any],
) -> None:
    """Queue an email once per idempotency key (duplicates are silently ignored)."""
    stmt = (
        insert(EmailOutbox)
        .values(
            idempotency_key=key,
            to_email=to,
            template=template,
            subject=subject,
            context=context,
            status="pending",
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
    )
    db.execute(stmt)


def build_message(settings: Settings, row: EmailOutbox) -> EmailMessage:
    text_body, html_body = render(
        row.template,
        {**row.context, "store_name": settings.store_name, "site_url": settings.public_site_url},
    )
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = row.to_email
    message["Subject"] = row.subject
    message["Message-ID"] = make_msgid(domain="store.local")
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    return message


def _send(settings: Settings, message: EmailMessage, row: EmailOutbox) -> str:
    """Send with the configured backend and return the resulting status."""
    backend = settings.email_backend
    if backend == "memory":
        MEMORY_OUTBOX.append(message)
        return "written_to_sink"
    if backend == "console":
        logger.info(
            "email (console backend)", extra={"template": row.template, "email_id": str(row.id)}
        )
        return "written_to_sink"
    if backend == "file":
        folder = settings.resolve_path(settings.email_file_dir)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = utcnow().strftime("%Y%m%d-%H%M%S")
        (folder / f"{stamp}-{row.template}-{row.id}.eml").write_bytes(bytes(message))
        return "written_to_sink"
    # SMTP
    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_starttls:
            smtp.starttls(context=context)
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)
    return "sent"


def dispatch_pending(
    session_factory: Callable[[], Session], settings: Settings, limit: int = 20
) -> int:
    """Send due emails; safe to run concurrently (SKIP LOCKED). Returns the number sent."""
    processed = 0
    with session_factory() as db:
        rows = db.scalars(
            select(EmailOutbox)
            .where(EmailOutbox.status == "pending", EmailOutbox.next_attempt_at <= utcnow())
            .order_by(EmailOutbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        for row in rows:
            row.attempts += 1
            try:
                status = _send(settings, build_message(settings, row), row)
            except Exception as exc:  # network/SMTP errors: retry with back-off
                row.last_error = f"{type(exc).__name__}: {exc}"[:2000]
                if row.attempts >= MAX_ATTEMPTS:
                    row.status = "failed"
                    logger.error("email failed permanently", extra={"email_id": str(row.id)})
                else:
                    row.next_attempt_at = utcnow() + timedelta(minutes=2**row.attempts)
                continue
            row.status = status
            row.sent_at = utcnow()
            row.last_error = None
            row.context = {}  # drop one-time links and personal details once delivered
            processed += 1
        db.commit()
    return processed
