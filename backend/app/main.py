"""FastAPI application factory.

Run locally:  .venv/Scripts/python -m uvicorn app.main:app --reload --port 8010
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.sitemap import router as sitemap_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.db import make_engine, make_session_factory
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    BodySizeLimitMiddleware,
    CSRFMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.jobs import job_loop

API_PREFIX = "/api/v1"
logger = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    engine = make_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("Starting %s API (env=%s)", settings.store_name, settings.app_env)
        jobs = (
            asyncio.create_task(job_loop(app.state.session_factory, settings))
            if settings.background_jobs_enabled
            else None
        )
        yield
        if jobs is not None:
            jobs.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await jobs
        engine.dispose()

    show_docs = not settings.is_production
    app = FastAPI(
        title=f"{settings.store_name} Store API",
        version="0.1.0",
        docs_url="/api/docs" if show_docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if show_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)

    register_exception_handlers(app)

    # Middleware: the LAST one added runs FIRST (outermost).
    app.add_middleware(
        CSRFMiddleware,
        allowed_origins=settings.allowed_origins,
        exempt_prefixes=(f"{API_PREFIX}/webhooks/",),
    )
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-Order-Access-Token"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
    app.add_middleware(RequestContextMiddleware)

    app.include_router(api_router, prefix=API_PREFIX)
    app.include_router(sitemap_router)
    return app


def _create_default_app() -> FastAPI:
    return create_app()


app = _create_default_app()
