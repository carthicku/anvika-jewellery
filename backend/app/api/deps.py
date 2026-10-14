"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from app.core.config import Settings


def get_app_settings(request: Request) -> Settings:
    """Settings of the running app (tests create apps with their own settings)."""
    settings: Settings = request.app.state.settings
    return settings
