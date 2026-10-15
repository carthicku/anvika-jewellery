"""Admin after-sales: return/exchange requests and review moderation.

Every route declares `require_permission(...)` (enforced by tests). Mutations are audited.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_request_meta, require_permission
from app.api.v1.routes.auth import send_emails_later
from app.core.config import Settings
from app.core.db import get_db
from app.core.errors import NotFound
from app.models import Order, Product, ProductReview, Refund, ReturnRequest, User
from app.schemas.admin import (
    AdminReturnLineOut,
    AdminReturnOut,
    AdminReturnRowOut,
    ReturnDecisionIn,
    ReturnReceiveIn,
    ReturnRefundIn,
)
from app.schemas.common import Page
from app.schemas.reviews import AdminReviewOut, ModerateReviewIn
from app.services import orders, returns, reviews
from app.services.auth import RequestMeta
from app.services.catalogue import page_count

router = APIRouter(prefix="/admin", tags=["admin"])

PageNo = Annotated[int, Query(ge=1, le=10_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]
ReturnStatusFilter = Literal["requested", "approved", "rejected", "received", "refunded", "closed"]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


# --------------------------------------------------------------------------------------------
# Returns
# --------------------------------------------------------------------------------------------


def _row(request: ReturnRequest, order: Order) -> AdminReturnRowOut:
    return AdminReturnRowOut(
        id=str(request.id),
        order_reference=order.reference,
        customer_name=order.customer_name,
        kind=request.kind,
        status=request.status,
        status_label=returns.STATUS_LABELS[request.status],
        item_count=sum(int(line["quantity"]) for line in request.items),
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def _detail(db: Session, request: ReturnRequest) -> AdminReturnOut:
    order = db.get(Order, request.order_id)
    if order is None:  # unreachable: the FK cascades on delete
        raise NotFound("Order not found.")
    refund = db.get(Refund, request.refund_id) if request.refund_id else None
    return AdminReturnOut(
        **_row(request, order).model_dump(),
        email=order.email,
        reason=request.reason,
        store_note=request.store_note,
        items=[
            AdminReturnLineOut(
                position=int(line["position"]),
                product_name=line["product_name"],
                variant_label=line["variant_label"],
                sku=line["sku"],
                quantity=int(line["quantity"]),
                restock=line.get("restock"),
            )
            for line in request.items
        ],
        delivered_at=returns.delivered_at(db, order),
        suggested_refund=returns.suggested_refund(db, request, order),
        refund_id=str(refund.id) if refund else None,
        refund_status=refund.status if refund else None,
        refund_amount=refund.amount if refund else None,
        allowed_actions=returns.allowed_actions(request),
    )


@router.get(
    "/returns",
    response_model=Page[AdminReturnRowOut],
    dependencies=[Depends(require_permission("orders:write"))],
)
def list_returns(
    response: Response,
    status: ReturnStatusFilter | None = None,
    page: PageNo = 1,
    page_size: PageSize = 25,
    db: Session = Depends(get_db),
) -> Page[AdminReturnRowOut]:
    _no_store(response)
    stmt = returns.filtered(status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        select(ReturnRequest, Order)
        .join(Order, Order.id == ReturnRequest.order_id)
        .where(ReturnRequest.id.in_(stmt.with_only_columns(ReturnRequest.id)))
        .order_by(ReturnRequest.created_at.desc(), ReturnRequest.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[_row(r, o) for r, o in rows],
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


@router.get(
    "/returns/{request_id}",
    response_model=AdminReturnOut,
    dependencies=[Depends(require_permission("orders:write"))],
)
def get_return(
    request_id: uuid.UUID, response: Response, db: Session = Depends(get_db)
) -> AdminReturnOut:
    _no_store(response)
    return _detail(db, returns.find(db, request_id))


def _locked(db: Session, request_id: uuid.UUID) -> tuple[ReturnRequest, Order]:
    """Lock the order first, then the request (same order as the customer endpoint)."""
    order = orders.lock_order(db, returns.find(db, request_id).order_id)
    return returns.find(db, request_id, lock=True), order


def _finish(
    db: Session, request: Request, tasks: BackgroundTasks, return_request: ReturnRequest
) -> AdminReturnOut:
    db.commit()
    out = _detail(db, return_request)
    db.commit()
    send_emails_later(request, tasks)
    return out


@router.post("/returns/{request_id}/approve", response_model=AdminReturnOut)
def approve_return(
    request_id: uuid.UUID,
    data: ReturnDecisionIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_permission("orders:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminReturnOut:
    return_request, order = _locked(db, request_id)
    returns.decide(
        db, settings, user, return_request, order, approve=True, note=data.note, ip=meta.ip
    )
    return _finish(db, request, tasks, return_request)


@router.post("/returns/{request_id}/reject", response_model=AdminReturnOut)
def reject_return(
    request_id: uuid.UUID,
    data: ReturnDecisionIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_permission("orders:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminReturnOut:
    return_request, order = _locked(db, request_id)
    returns.decide(
        db, settings, user, return_request, order, approve=False, note=data.note, ip=meta.ip
    )
    return _finish(db, request, tasks, return_request)


@router.post("/returns/{request_id}/receive", response_model=AdminReturnOut)
def receive_return(
    request_id: uuid.UUID,
    data: ReturnReceiveIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_permission("orders:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminReturnOut:
    return_request, order = _locked(db, request_id)
    returns.receive(
        db,
        settings,
        user,
        return_request,
        order,
        restock_positions=set(data.restock_positions),
        note=data.note,
        ip=meta.ip,
    )
    return _finish(db, request, tasks, return_request)


@router.post("/returns/{request_id}/refund", response_model=AdminReturnOut)
def refund_return(
    request_id: uuid.UUID,
    data: ReturnRefundIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_permission("orders:refund")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminReturnOut:
    """Record the refund request; it is sent to the payment provider from the order page."""
    return_request, order = _locked(db, request_id)
    returns.refund(
        db, settings, user, return_request, order, amount=data.amount, note=data.note, ip=meta.ip
    )
    return _finish(db, request, tasks, return_request)


@router.post("/returns/{request_id}/close", response_model=AdminReturnOut)
def close_return(
    request_id: uuid.UUID,
    data: ReturnDecisionIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_permission("orders:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminReturnOut:
    return_request, order = _locked(db, request_id)
    returns.close(db, settings, user, return_request, order, note=data.note, ip=meta.ip)
    return _finish(db, request, tasks, return_request)


# --------------------------------------------------------------------------------------------
# Reviews
# --------------------------------------------------------------------------------------------


def _review(review: ProductReview, product: Product, user: User) -> AdminReviewOut:
    return AdminReviewOut(
        id=str(review.id),
        product_name=product.name,
        product_slug=product.slug,
        rating=review.rating,
        title=review.title,
        body=review.body,
        author_name=review.author_name,
        customer_email=user.email,
        verified_purchase=review.order_item_id is not None,
        status=review.status,
        moderation_note=review.moderation_note,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _review_with_refs(db: Session, review: ProductReview) -> AdminReviewOut:
    product = db.get(Product, review.product_id)
    user = db.get(User, review.user_id)
    if product is None or user is None:  # unreachable: the FKs cascade on delete
        raise NotFound("Review not found.")
    return _review(review, product, user)


@router.get(
    "/reviews",
    response_model=Page[AdminReviewOut],
    dependencies=[Depends(require_permission("content:write"))],
)
def list_reviews(
    response: Response,
    status: Literal["pending", "approved", "rejected"] | None = None,
    page: PageNo = 1,
    page_size: PageSize = 25,
    db: Session = Depends(get_db),
) -> Page[AdminReviewOut]:
    _no_store(response)
    stmt = reviews.filtered(status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        select(ProductReview, Product, User)
        .join(Product, Product.id == ProductReview.product_id)
        .join(User, User.id == ProductReview.user_id)
        .where(ProductReview.id.in_(stmt.with_only_columns(ProductReview.id)))
        .order_by(ProductReview.updated_at.desc(), ProductReview.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[_review(r, p, u) for r, p, u in rows],
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


@router.post("/reviews/{review_id}/moderate", response_model=AdminReviewOut)
def moderate_review(
    review_id: uuid.UUID,
    data: ModerateReviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("content:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminReviewOut:
    review = reviews.find(db, review_id)
    reviews.moderate(db, user, review, decision=data.decision, note=data.note, ip=meta.ip)
    db.commit()
    out = _review_with_refs(db, review)
    db.commit()
    return out
