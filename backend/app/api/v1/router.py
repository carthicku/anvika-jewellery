"""Collects every v1 route module under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import account, auth, cart, catalogue, content, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalogue.router)
api_router.include_router(content.router)
api_router.include_router(account.router)
api_router.include_router(cart.router)
