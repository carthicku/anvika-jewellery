"""Shared pytest fixtures.

* The test database is rebuilt from migrations once per test session (proving the migration chain).
* Each test runs inside an outer transaction that is rolled back, so tests don't affect each other.
  Code under test may call `commit()` freely: the session joins the outer transaction with
  savepoints (SQLAlchemy "join_transaction_mode").
* SAFETY: refuses to touch any database whose name does not end with "_test".
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKEND_DIR, Settings, get_settings
from app.core.db import make_engine
from app.main import create_app
from app.seed import run_seed


def _test_settings(**overrides: object) -> Settings:
    base = get_settings()
    values: dict[str, object] = {
        "app_env": "test",
        "database_url": base.test_database_url,
        "test_database_url": base.test_database_url,
        "email_backend": "memory",
        "payment_provider": "simulator",
        "background_jobs_enabled": False,
        "cookie_secure": False,
        "allowed_origins": ["http://localhost:5180"],
        "public_site_url": "http://localhost:5180",
        "log_level": "WARNING",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture(scope="session")
def settings() -> Settings:
    return _test_settings()


@pytest.fixture(scope="session")
def engine(settings: Settings) -> Iterator[Engine]:
    url = make_url(settings.database_url)
    if not (url.database or "").endswith("_test"):
        pytest.exit(f"Refusing to run tests against non-test database {url.database!r}", 2)
    eng = make_engine(settings.database_url)
    with eng.begin() as conn:
        encoding = conn.execute(text("SHOW server_encoding")).scalar()
        if encoding != "UTF8":
            pytest.exit(
                f"Test database encoding is {encoding}; it must be UTF8 (like Supabase).", 2
            )
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = settings.database_url
    cfg.attributes["skip_logging_config"] = True
    command.upgrade(cfg, "head")
    # Committed once per session; every test runs in a rolled-back transaction on top of it.
    with Session(eng) as session:
        run_seed(session)
        session.commit()
    yield eng
    eng.dispose()


@pytest.fixture()
def connection(engine: Engine) -> Iterator[Connection]:
    conn = engine.connect()
    outer = conn.begin()
    try:
        yield conn
    finally:
        outer.rollback()
        conn.close()


@pytest.fixture()
def db(connection: Connection) -> Iterator[Session]:
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def app(settings: Settings, connection: Connection) -> FastAPI:
    application = create_app(settings)
    application.state.session_factory = sessionmaker(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
        autoflush=False,
    )
    return application


@pytest.fixture()
def raw_client(app: FastAPI) -> Iterator[TestClient]:
    """A client WITHOUT the CSRF header — for testing CSRF protection itself."""
    with TestClient(app, base_url="http://testserver") as client:
        yield client


@pytest.fixture()
def client(raw_client: TestClient) -> TestClient:
    """A browser-like client: holds cookies and sends the CSRF header on every request."""
    response = raw_client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    raw_client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return raw_client


@pytest.fixture()
def make_settings() -> object:
    """Factory for tests that need settings variations (e.g. production validation)."""
    return _test_settings
