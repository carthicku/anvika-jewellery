"""Health checks used by uptime monitors and deploy smoke tests."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ServiceUnavailable

router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: Literal["ok"]
    database: Literal["ok", "not_checked"] = "not_checked"
    migration: str | None = None


@router.get("/health", response_model=HealthOut)
def health(deep: bool = Query(False), db: Session = Depends(get_db)) -> HealthOut:
    """Cheap liveness check; `?deep=true` also checks the database and migration revision."""
    if not deep:
        return HealthOut(status="ok")
    try:
        db.execute(text("SELECT 1"))
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception as exc:
        raise ServiceUnavailable("Database is not reachable.") from exc
    return HealthOut(status="ok", database="ok", migration=revision)
