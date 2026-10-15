"""In-process background jobs (docs/architecture/SYSTEM_ARCHITECTURE.md §5).

Runs every JOB_INTERVAL_SECONDS while BACKGROUND_JOBS_ENABLED=true. Each job is safe to run on
several app instances at once (row locks with SKIP LOCKED) and can also be triggered manually with
`python -m app.cli run-jobs`. Correctness never depends on these running on time.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.services import email as email_service
from app.services import payments
from app.services.catalogue import refresh_price_cache
from app.services.payment_gateway import PaymentGateway

logger = logging.getLogger("app.jobs")
JOB_INTERVAL_SECONDS = 30
PRICE_REFRESH_EVERY = 20  # runs (≈ 10 minutes)


def run_once(
    session_factory: Callable[[], Session],
    settings: Settings,
    gateway: PaymentGateway,
    *,
    include_unexpired: bool = False,
) -> payments.ReconcileReport:
    """Expire/reconcile pending orders, then send queued emails (including the ones those
    steps just queued)."""
    with session_factory() as db:
        report = payments.expire_and_reconcile(
            db, settings, gateway, include_unexpired=include_unexpired
        )
    if report.checked:
        logger.info("payments reconciled: %s", payments.describe(report))
    email_service.dispatch_pending(session_factory, settings)
    return report


def refresh_prices(session_factory: Callable[[], Session]) -> None:
    """Refresh the listing price cache (catches discounts starting/ending)."""
    with session_factory() as db:
        refresh_price_cache(db)
        db.commit()


async def job_loop(
    session_factory: Callable[[], Session], settings: Settings, gateway: PaymentGateway
) -> None:
    runs = 0
    while True:
        try:
            await run_in_threadpool(run_once, session_factory, settings, gateway)
            if runs % PRICE_REFRESH_EVERY == 0:
                await run_in_threadpool(refresh_prices, session_factory)
        except Exception:  # keep the loop alive; the error is logged with a traceback
            logger.exception("background job run failed")
        runs += 1
        await asyncio.sleep(JOB_INTERVAL_SECONDS)
