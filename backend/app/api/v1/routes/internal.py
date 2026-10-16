"""Scheduled-job endpoints for hosts without a long-running process (Vercel Cron).

On a serverless host the in-process job loop can't run (functions are frozen between requests), so
the scheduler calls these URLs instead. They do exactly what `python -m app.cli run-jobs` and
`refresh-prices` do. Protected by `CRON_SECRET`: Vercel sends it as `Authorization: Bearer …`
automatically when a project variable of that name exists. Without the secret the endpoints
don't exist (404), so a store that doesn't use them exposes nothing.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, Request, Response
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_app_settings, get_gateway
from app.core.config import Settings
from app.core.errors import NotAuthenticated, NotFound
from app.jobs import refresh_prices, run_once
from app.services.payment_gateway import PaymentGateway

router = APIRouter(prefix="/internal/cron", tags=["internal"], include_in_schema=False)


def require_cron_secret(
    response: Response,
    settings: Settings = Depends(get_app_settings),
    authorization: str | None = Header(default=None, max_length=300),
) -> None:
    response.headers["Cache-Control"] = "no-store"
    secret = settings.cron_secret.get_secret_value()
    if not secret:
        raise NotFound("Not found.")
    expected = f"Bearer {secret}"
    if not hmac.compare_digest((authorization or "").encode(), expected.encode()):
        raise NotAuthenticated("Invalid cron credentials.")


@router.get("/run-jobs", dependencies=[Depends(require_cron_secret)])
async def run_jobs(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    gateway: PaymentGateway = Depends(get_gateway),
) -> dict[str, int]:
    """Expire/reconcile pending orders and send queued emails (safe to run twice or overlapping:
    rows are claimed with SKIP LOCKED and every step is idempotent)."""
    report = await run_in_threadpool(run_once, request.app.state.session_factory, settings, gateway)
    return {
        "checked": report.checked,
        "paid": report.paid,
        "expired": report.expired,
        "review": report.review,
        "errors": report.errors,
    }


@router.get("/refresh-prices", dependencies=[Depends(require_cron_secret)])
async def refresh_listing_prices(request: Request) -> dict[str, bool]:
    """Refresh the listing price cache (catches discounts that start or end)."""
    await run_in_threadpool(refresh_prices, request.app.state.session_factory)
    return {"ok": True}
