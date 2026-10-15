"""Collects every v1 route module under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    account,
    auth,
    cart,
    catalogue,
    checkout,
    content,
    health,
    orders,
    payments,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalogue.router)
api_router.include_router(content.router)
api_router.include_router(account.router)
api_router.include_router(cart.router)
api_router.include_router(checkout.router)
api_router.include_router(payments.router)
api_router.include_router(payments.webhook_router)
api_router.include_router(orders.router)
