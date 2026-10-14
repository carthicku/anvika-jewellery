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

logger = logging.getLogger("app.jobs")
JOB_INTERVAL_SECONDS = 30


def run_once(session_factory: Callable[[], Session], settings: Settings) -> None:
    email_service.dispatch_pending(session_factory, settings)


async def job_loop(session_factory: Callable[[], Session], settings: Settings) -> None:
    while True:
        try:
            await run_in_threadpool(run_once, session_factory, settings)
        except Exception:  # keep the loop alive; the error is logged with a traceback
            logger.exception("background job run failed")
        await asyncio.sleep(JOB_INTERVAL_SECONDS)
