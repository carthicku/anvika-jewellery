"""Verified-purchase product reviews with moderation (ASSUMPTIONS_AND_DECISIONS.md B5).

* Only signed-in customers whose order containing the product was delivered can write a review.
* Every new or edited review waits for staff approval; only `approved` reviews are public, and
  the rating summary (and any structured data built from it) counts approved reviews only.
* Nothing is seeded: a product with no approved reviews simply shows none.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.core.time import utcnow
from app.models import Order, OrderItem, Product, ProductReview, User
from app.services import audit

REVIEWABLE_ORDER_STATUSES = ("delivered", "returned")


@dataclass
class Summary:
    count: int
    average: Decimal | None  # one decimal place, None when there are no approved reviews


def active_product(db: Session, slug: str) -> Product:
    product = db.scalar(select(Product).where(Product.slug == slug, Product.status == "active"))
    if product is None:
        raise NotFound("Product not found.")
    return product


def public_name(full_name: str) -> str:
    """ "Asha Rao" → "Asha R."; a single name is shown as is. Never the email address."""
    parts = full_name.split()
    if not parts:
        return "Customer"
    if len(parts) == 1:
        return parts[0][:60]
    return f"{parts[0][:56]} {parts[-1][0].upper()}."


def summary(db: Session, product_id: uuid.UUID) -> Summary:
    count, average = db.execute(
        select(func.count(), func.avg(ProductReview.rating)).where(
            ProductReview.product_id == product_id, ProductReview.status == "approved"
        )
    ).one()
    if not count:
        return Summary(0, None)
    return Summary(int(count), Decimal(average).quantize(Decimal("0.1"), ROUND_HALF_UP))


def approved(
    db: Session, product_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[ProductReview], int]:
    stmt = select(ProductReview).where(
        ProductReview.product_id == product_id, ProductReview.status == "approved"
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ProductReview.created_at.desc(), ProductReview.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def delivered_purchase(db: Session, user: User, product: Product) -> OrderItem | None:
    """The customer's most recent delivered order line for this product, if any."""
    return db.scalar(
        select(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.user_id == user.id,
            Order.status.in_(REVIEWABLE_ORDER_STATUSES),
            OrderItem.product_id == product.id,
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )


def mine(db: Session, user: User, product: Product) -> ProductReview | None:
    return db.scalar(
        select(ProductReview).where(
            ProductReview.user_id == user.id, ProductReview.product_id == product.id
        )
    )


def submit(
    db: Session, user: User, product: Product, *, rating: int, title: str, body: str
) -> ProductReview:
    """Create or edit the customer's review. Either way it goes (back) to moderation."""
    item = delivered_purchase(db, user, product)
    if item is None:
        raise Forbidden(
            "Reviews can be written once an order containing this piece has been delivered.",
            code="NOT_A_VERIFIED_PURCHASE",
        )
    title, body = title.strip(), body.strip()
    if not 1 <= rating <= 5:
        raise ValidationFailed({"rating": "Choose 1 to 5 stars."})
    if len(title) < 3:
        raise ValidationFailed({"title": "Add a short title."})
    if len(body) < 20:
        raise ValidationFailed({"body": "Please write at least 20 characters."})
    review = db.scalar(
        select(ProductReview)
        .where(ProductReview.user_id == user.id, ProductReview.product_id == product.id)
        .with_for_update()
    )
    if review is None:
        review = ProductReview(user_id=user.id, product_id=product.id)
        db.add(review)
    review.order_item_id = item.id
    review.rating = rating
    review.title = title[:120]
    review.body = body[:2000]
    review.author_name = public_name(user.full_name)
    review.status = "pending"
    review.moderation_note = None
    review.moderated_by = None
    review.moderated_at = None
    review.updated_at = utcnow()
    db.flush()
    return review


# --------------------------------------------------------------------------------------------
# Moderation
# --------------------------------------------------------------------------------------------


def filtered(status: str | None) -> Select[ProductReview]:
    stmt = select(ProductReview)
    if status:
        stmt = stmt.where(ProductReview.status == status)
    return stmt


def find(db: Session, review_id: uuid.UUID) -> ProductReview:
    review = db.scalar(select(ProductReview).where(ProductReview.id == review_id).with_for_update())
    if review is None:
        raise NotFound("Review not found.")
    return review


def moderate(
    db: Session,
    actor: User,
    review: ProductReview,
    *,
    decision: str,
    note: str,
    ip: str | None = None,
) -> None:
    if decision not in ("approve", "reject"):
        raise ValidationFailed({"decision": "Choose approve or reject."})
    status = "approved" if decision == "approve" else "rejected"
    if review.status == status:
        raise Conflict(f"This review is already {status}.", code="REVIEW_UNCHANGED")
    review.status = status
    review.moderation_note = note.strip()[:300] or None
    review.moderated_by = actor.id
    review.moderated_at = utcnow()
    audit.record(
        db,
        actor=actor,
        action=f"review.{status}",
        entity_type="product_review",
        entity_id=review.id,
        changes={"status": status, "note": review.moderation_note},
        ip_address=ip,
    )
    db.flush()
