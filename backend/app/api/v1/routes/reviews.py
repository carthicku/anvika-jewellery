"""Product reviews: the public list of approved reviews, and a signed-in customer's own review.

Only customers with a delivered order containing the product can write one; every new or edited
review waits for staff approval (docs/architecture/API_CONTRACT.md → Reviews).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.rate_limit import rate_limit
from app.models import ProductReview, User
from app.schemas.common import Page
from app.schemas.reviews import (
    MyReviewOut,
    MyReviewStateOut,
    ProductReviewsOut,
    ReviewIn,
    ReviewOut,
    ReviewSummaryOut,
)
from app.services import reviews
from app.services.catalogue import page_count

router = APIRouter(tags=["reviews"])

STATUS_LABELS = {
    "pending": "Waiting for approval",
    "approved": "Published",
    "rejected": "Not published",
}


def _mine(review: ProductReview | None) -> MyReviewOut | None:
    if review is None:
        return None
    return MyReviewOut(
        rating=review.rating,
        title=review.title,
        body=review.body,
        status=review.status,
        status_label=STATUS_LABELS[review.status],
        updated_at=review.updated_at,
    )


@router.get("/products/{slug}/reviews", response_model=ProductReviewsOut)
def product_reviews(
    slug: str,
    response: Response,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
    db: Session = Depends(get_db),
) -> ProductReviewsOut:
    """Approved reviews only, newest first, with a summary counted from approved reviews."""
    # Revalidated on every load so a newly published (or removed) review shows straight away.
    response.headers["Cache-Control"] = "no-cache"
    product = reviews.active_product(db, slug[:180])
    summary = reviews.summary(db, product.id)
    rows, total = reviews.approved(db, product.id, page, page_size)
    return ProductReviewsOut(
        summary=ReviewSummaryOut(
            count=summary.count,
            average=str(summary.average) if summary.average is not None else None,
        ),
        reviews=Page(
            items=[
                ReviewOut(
                    id=str(r.id),
                    rating=r.rating,
                    title=r.title,
                    body=r.body,
                    author_name=r.author_name,
                    verified_purchase=r.order_item_id is not None,
                    created_at=r.created_at,
                )
                for r in rows
            ],
            page=page,
            page_size=page_size,
            total=total,
            pages=page_count(total, page_size),
        ),
    )


@router.get("/products/{slug}/reviews/mine", response_model=MyReviewStateOut)
def my_review(
    slug: str,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MyReviewStateOut:
    response.headers["Cache-Control"] = "no-store"
    product = reviews.active_product(db, slug[:180])
    return MyReviewStateOut(
        can_review=reviews.delivered_purchase(db, user, product) is not None,
        review=_mine(reviews.mine(db, user, product)),
    )


@router.put(
    "/products/{slug}/reviews/mine",
    response_model=MyReviewStateOut,
    dependencies=[Depends(rate_limit("review", limit=10, window_seconds=3600))],
)
def save_my_review(
    slug: str,
    data: ReviewIn,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MyReviewStateOut:
    """Write or edit your review. It is published after a member of staff approves it."""
    response.headers["Cache-Control"] = "no-store"
    product = reviews.active_product(db, slug[:180])
    review = reviews.submit(db, user, product, rating=data.rating, title=data.title, body=data.body)
    db.commit()
    return MyReviewStateOut(can_review=True, review=_mine(review))
