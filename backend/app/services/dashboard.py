"""Admin dashboard figures. Revenue counts only orders with a verified payment; unpaid, expired and
cancelled-before-payment orders never inflate sales."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.money import ZERO
from app.core.time import utcnow
from app.models import InventoryLevel, Order, OrderItem, Product, ProductVariant, Refund
from app.services import gold_rates
from app.services.shipping import IST

PAID_STATES = ("paid", "refund_pending", "partially_refunded", "refunded")


@dataclass
class LowStockRow:
    sku: str
    product_name: str
    variant_label: str
    available: int
    threshold: int


@dataclass
class BestSeller:
    product_name: str
    product_slug: str
    quantity: int


@dataclass
class Dashboard:
    date_from: datetime
    date_to: datetime
    paid_orders: int
    paid_revenue: Decimal
    refunded: Decimal
    paid_orders_today: int
    pending_payment: int
    payment_review: int
    to_fulfil: int
    recent: list[Order]
    review_orders: list[Order]
    low_stock: list[LowStockRow]
    best_sellers: list[BestSeller]
    rates: list[gold_rates.RateStatus] = field(default_factory=list)


def start_of_ist_day(moment: datetime) -> datetime:
    local = moment.astimezone(IST)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def build(db: Session, date_from: datetime | None, date_to: datetime | None) -> Dashboard:
    now = utcnow()
    date_to = date_to or now
    date_from = date_from or (start_of_ist_day(now) - timedelta(days=29))
    in_range = (Order.paid_at >= date_from) & (Order.paid_at < date_to)
    paid = Order.payment_status.in_(PAID_STATES)

    paid_orders = db.scalar(select(func.count()).select_from(Order).where(paid, in_range)) or 0
    paid_revenue = db.scalar(
        select(func.coalesce(func.sum(Order.grand_total), ZERO)).where(paid, in_range)
    )
    refunded = db.scalar(
        select(func.coalesce(func.sum(Refund.amount), ZERO)).where(
            Refund.status == "processed",
            Refund.updated_at >= date_from,
            Refund.updated_at < date_to,
        )
    )
    today = start_of_ist_day(now)
    paid_today = (
        db.scalar(select(func.count()).select_from(Order).where(paid, Order.paid_at >= today)) or 0
    )

    def count(status: str) -> int:
        return db.scalar(select(func.count()).select_from(Order).where(Order.status == status)) or 0

    review_orders = list(
        db.scalars(
            select(Order).where(Order.status == "payment_review").order_by(Order.updated_at)
        ).all()
    )
    recent = list(
        db.scalars(
            select(Order)
            .where(Order.status.not_in(("expired",)))
            .order_by(Order.created_at.desc())
            .limit(10)
        ).all()
    )
    available = InventoryLevel.on_hand - InventoryLevel.reserved
    low_rows = db.execute(
        select(
            ProductVariant.sku,
            Product.name,
            ProductVariant.label,
            available.label("available"),
            InventoryLevel.low_stock_threshold,
        )
        .join(ProductVariant, ProductVariant.id == InventoryLevel.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(
            Product.status == "active",
            ProductVariant.is_active.is_(True),
            available <= InventoryLevel.low_stock_threshold,
        )
        .order_by(available, Product.name)
        .limit(20)
    ).all()
    sellers = db.execute(
        select(
            OrderItem.product_name,
            OrderItem.product_slug,
            func.sum(OrderItem.quantity).label("qty"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(paid, in_range, Order.status.not_in(("cancelled", "returned")))
        .group_by(OrderItem.product_name, OrderItem.product_slug)
        .order_by(func.sum(OrderItem.quantity).desc(), OrderItem.product_name)
        .limit(5)
    ).all()
    return Dashboard(
        date_from=date_from,
        date_to=date_to,
        paid_orders=paid_orders,
        paid_revenue=paid_revenue or ZERO,
        refunded=refunded or ZERO,
        paid_orders_today=paid_today,
        pending_payment=count("pending_payment"),
        payment_review=len(review_orders),
        to_fulfil=count("confirmed") + count("processing"),
        recent=recent,
        review_orders=review_orders,
        low_stock=[LowStockRow(r[0], r[1], r[2], int(r[3]), int(r[4])) for r in low_rows],
        best_sellers=[BestSeller(r[0], r[1], int(r[2])) for r in sellers],
        rates=gold_rates.current_status(db, now),
    )
