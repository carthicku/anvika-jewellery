"""Database-level safety nets that must hold for every table (ADR-0002, ADR-0007)."""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import InventoryLevel


def test_every_application_table_has_row_level_security(db: Session) -> None:
    rows = db.execute(
        text(
            """
            SELECT c.relname, c.relrowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> 'alembic_version'
            """
        )
    ).all()
    assert rows, "no tables found"
    missing = sorted(name for name, rls in rows if not rls)
    assert missing == [], f"Tables without RLS (add ENABLE ROW LEVEL SECURITY): {missing}"


def test_database_rejects_negative_or_over_reserved_stock(db: Session) -> None:
    level = db.scalars(select(InventoryLevel).limit(1)).one()
    level.reserved = level.on_hand + 1
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_sessions_use_utc(db: Session) -> None:
    assert db.execute(text("SHOW timezone")).scalar() == "UTC"
