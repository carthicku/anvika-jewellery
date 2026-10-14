"""Database engine and sessions (SQLAlchemy 2.x, synchronous, psycopg 3). See ADR-0004."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(url: str, *, pool_size: int = 5, max_overflow: int = 5) -> Engine:
    return create_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,  # survive idle connections dropped by poolers/firewalls
        pool_recycle=1800,
        # The API speaks UTC; never inherit the server machine's timezone.
        connect_args={"options": "-c timezone=UTC"},
    )


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False lets routes return ORM objects after committing.
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def get_db(request: Request) -> Iterator[Session]:
    """FastAPI dependency: one session per request, rolled back if the request fails.

    Routes call `db.commit()` explicitly once the service has finished its unit of work.
    """
    factory: sessionmaker[Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
