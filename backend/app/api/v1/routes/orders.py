"""Customer order history, order detail (owner or guest token) and cancellation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import (
    Auth,
    get_app_settings,
    get_current_user,
    get_optional_auth,
    get_order_access_token,
)
from app.api.v1.routes.auth import send_emails_later
from app.core.config import Settings
from app.core.db import get_db
from app.core.errors import Conflict
from app.models import User
from app.schemas.common import Page
from app.schemas.orders import CancelOrderIn, OrderOut, OrderSummaryOut
from app.services import orders

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=Page[OrderSummaryOut])
def list_my_orders(
    response: Response,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[OrderSummaryOut]:
    response.headers["Cache-Control"] = "no-store"
    return orders.list_orders(db, user, page, page_size)


@router.get("/{reference}", response_model=OrderOut)
def get_order(
    reference: str,
    response: Response,
    db: Session = Depends(get_db),
    auth: Auth | None = Depends(get_optional_auth),
    access_token: str | None = Depends(get_order_access_token),
) -> OrderOut:
    """Your own order, or a guest order with its private access token. Anything else is 404."""
    response.headers["Cache-Control"] = "no-store"
    order = orders.find_order(db, reference[:24], auth.user if auth else None, access_token)
    return orders.order_view(db, order)


@router.post("/{reference}/cancel", response_model=OrderOut)
def cancel_order(
    reference: str,
    data: CancelOrderIn,
    request: Request,
    response: Response,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    auth: Auth | None = Depends(get_optional_auth),
    access_token: str | None = Depends(get_order_access_token),
) -> OrderOut:
    """Cancel before payment, or after payment until we start preparing the order."""
    response.headers["Cache-Control"] = "no-store"
    user = auth.user if auth else None
    order = orders.find_order(db, reference[:24], user, access_token, lock=True)
    if not orders.can_customer_cancel(order):
        if order.status == "pending_payment" and order.payment_status == "authorized":
            raise Conflict(
                "A payment for this order is still being confirmed, so it can't be cancelled "
                "yet. Please try again in a few minutes.",
                code="PAYMENT_IN_PROGRESS",
            )
        raise Conflict(
            "This order can no longer be cancelled online. Please contact us for help.",
            code="CANNOT_CANCEL",
        )
    orders.cancel_order(
        db,
        settings,
        order,
        actor_type="customer",
        actor_user_id=user.id if user else None,
        reason=data.reason,
    )
    db.commit()
    out = orders.order_view(db, order)
    db.commit()  # end the read transaction before the after-response work
    send_emails_later(request, tasks)
    return out
