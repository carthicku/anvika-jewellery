"""Read-only health checks for operators (docs/operations/MONITORING.md):

* `integrity_problems` — money and stock invariants that should always hold. Any result is a bug or
  a manual database edit to investigate; nothing is changed automatically.
* `rls_problems` — every application table has row-level security on and no policies (ADR-0002),
  so Supabase's public Data API can't read or write anything.
* `catalogue_report` — what still needs the owner's attention before launch (sample products,
  placeholder photos, missing hallmark details, unpriced pieces).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.money import ZERO
from app.core.time import utcnow
from app.models import (
    EmailOutbox,
    InventoryLevel,
    InventoryMovement,
    InventoryReservation,
    Order,
    OrderItem,
    PaymentAttempt,
    Product,
    ProductImage,
    ProductVariant,
    Refund,
)

PAID_STATES = ("paid", "refund_pending", "partially_refunded", "refunded")
# How long a pending order may stay past its payment window before the expiry job looks broken.
EXPIRY_GRACE = timedelta(minutes=30)


@dataclass
class Problem:
    check: str
    detail: str


def _limit(rows: list[Problem], check: str, total: int) -> list[Problem]:
    if total > len(rows):
        rows.append(Problem(check, f"… and {total - len(rows)} more"))
    return rows


def integrity_problems(db: Session, sample_limit: int = 20) -> list[Problem]:
    problems: list[Problem] = []

    # Stock: the ledger explains every unit on hand, and `reserved` matches the active holds.
    ledger = (
        select(
            InventoryMovement.variant_id,
            func.sum(InventoryMovement.delta_on_hand).label("on_hand"),
        )
        .group_by(InventoryMovement.variant_id)
        .subquery()
    )
    holds = (
        select(
            InventoryReservation.variant_id,
            func.sum(InventoryReservation.quantity).label("reserved"),
        )
        .where(InventoryReservation.status == "active")
        .group_by(InventoryReservation.variant_id)
        .subquery()
    )
    stock_rows = db.execute(
        select(
            ProductVariant.sku,
            InventoryLevel.on_hand,
            InventoryLevel.reserved,
            func.coalesce(ledger.c.on_hand, 0),
            func.coalesce(holds.c.reserved, 0),
        )
        .join(ProductVariant, ProductVariant.id == InventoryLevel.variant_id)
        .outerjoin(ledger, ledger.c.variant_id == InventoryLevel.variant_id)
        .outerjoin(holds, holds.c.variant_id == InventoryLevel.variant_id)
        .order_by(ProductVariant.sku)
    ).all()
    for sku, on_hand, reserved, ledger_on_hand, held in stock_rows:
        if on_hand != ledger_on_hand:
            problems.append(
                Problem("stock_ledger", f"{sku}: on hand {on_hand}, ledger says {ledger_on_hand}")
            )
        if reserved != held:
            problems.append(
                Problem("stock_reserved", f"{sku}: reserved {reserved}, active holds {held}")
            )
        if reserved < 0 or reserved > on_hand:
            problems.append(
                Problem("stock_range", f"{sku}: on hand {on_hand}, reserved {reserved}")
            )

    # Order arithmetic: totals agree with their parts (all Decimal, exact).
    line_sum = (
        select(OrderItem.order_id, func.sum(OrderItem.line_total).label("lines"))
        .group_by(OrderItem.order_id)
        .subquery()
    )
    lines = func.coalesce(line_sum.c.lines, ZERO)
    mismatch = (
        (Order.taxable_total != Order.subtotal - Order.automatic_discount - Order.coupon_discount)
        | (
            Order.grand_total
            != Order.taxable_total
            + Order.tax_total
            + Order.shipping_total
            + Order.rounding_adjustment
        )
        | (Order.grand_total != lines + Order.shipping_total + Order.rounding_adjustment)
    )
    total = db.scalar(
        select(func.count())
        .select_from(Order)
        .outerjoin(line_sum, line_sum.c.order_id == Order.id)
        .where(mismatch)
    )
    rows = [
        Problem("order_totals", f"{ref}: grand total {grand} doesn't add up")
        for ref, grand in db.execute(
            select(Order.reference, Order.grand_total)
            .outerjoin(line_sum, line_sum.c.order_id == Order.id)
            .where(mismatch)
            .limit(sample_limit)
        ).all()
    ]
    problems += _limit(rows, "order_totals", total or 0)

    # Paid orders have a payment time and a captured payment behind them.
    captured = select(PaymentAttempt.id).where(
        PaymentAttempt.order_id == Order.id, PaymentAttempt.status == "captured"
    )
    for ref, status, paid_at in db.execute(
        select(Order.reference, Order.payment_status, Order.paid_at)
        .where(Order.payment_status.in_(PAID_STATES), ~captured.exists())
        .limit(sample_limit)
    ).all():
        problems.append(Problem("paid_without_capture", f"{ref}: {status}, paid_at {paid_at}"))
    for (ref,) in db.execute(
        select(Order.reference)
        .where(Order.payment_status.in_(PAID_STATES), Order.paid_at.is_(None))
        .limit(sample_limit)
    ).all():
        problems.append(Problem("paid_without_time", f"{ref}: paid but no paid_at"))

    # Refunds never exceed what was paid.
    refunded = (
        select(Refund.order_id, func.sum(Refund.amount).label("amount"))
        .where(Refund.status != "failed")
        .group_by(Refund.order_id)
        .subquery()
    )
    for ref, grand, amount in db.execute(
        select(Order.reference, Order.grand_total, refunded.c.amount)
        .join(refunded, refunded.c.order_id == Order.id)
        .where(refunded.c.amount > Order.grand_total)
        .limit(sample_limit)
    ).all():
        problems.append(Problem("over_refund", f"{ref}: refunds {amount} > paid {grand}"))

    # Background jobs are running: nothing sits long past its payment window or in the outbox.
    overdue = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.status == "pending_payment",
            Order.payment_expires_at < utcnow() - EXPIRY_GRACE,
        )
    )
    if overdue:
        problems.append(
            Problem(
                "jobs_not_running",
                f"{overdue} pending orders are more than {EXPIRY_GRACE} past their payment "
                "window — is `python -m app.cli run-jobs` scheduled?",
            )
        )
    failed_mail = db.scalar(
        select(func.count()).select_from(EmailOutbox).where(EmailOutbox.status == "failed")
    )
    if failed_mail:
        problems.append(Problem("email_failed", f"{failed_mail} emails failed permanently"))
    return problems


def rls_problems(db: Session) -> list[Problem]:
    problems: list[Problem] = []
    rows = db.execute(
        text(
            """
            SELECT c.relname, c.relrowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> 'alembic_version'
            ORDER BY c.relname
            """
        )
    ).all()
    if not rows:
        problems.append(Problem("rls", "no application tables found — wrong database?"))
    for name, enabled in rows:
        if not enabled:
            problems.append(Problem("rls_disabled", f"{name}: row-level security is off"))
    for table, policy in db.execute(
        text("SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public'")
    ).all():
        problems.append(
            Problem("rls_policy", f"{table}: policy {policy!r} exists (ADR-0002 expects none)")
        )
    return problems


@dataclass
class CatalogueReport:
    by_status: dict[str, int]
    samples: list[str] = field(default_factory=list)
    placeholder_images: list[str] = field(default_factory=list)
    no_images: list[str] = field(default_factory=list)
    missing_hallmark: list[str] = field(default_factory=list)
    unpriced: list[str] = field(default_factory=list)

    @property
    def launch_blockers(self) -> int:
        return len(self.samples) + len(self.unpriced)


def catalogue_report(db: Session) -> CatalogueReport:
    by_status = {
        status: count
        for status, count in db.execute(
            select(Product.status, func.count()).group_by(Product.status)
        ).all()
    }
    active = Product.status == "active"
    report = CatalogueReport(by_status=by_status)
    report.samples = list(
        db.scalars(select(Product.slug).where(active, Product.is_sample).order_by(Product.slug))
    )
    has_real = select(ProductImage.id).where(
        ProductImage.product_id == Product.id, ProductImage.is_placeholder.is_(False)
    )
    has_any = select(ProductImage.id).where(ProductImage.product_id == Product.id)
    report.placeholder_images = list(
        db.scalars(
            select(Product.slug)
            .where(active, has_any.exists(), ~has_real.exists())
            .order_by(Product.slug)
        )
    )
    report.no_images = list(
        db.scalars(select(Product.slug).where(active, ~has_any.exists()).order_by(Product.slug))
    )
    report.missing_hallmark = list(
        db.scalars(
            select(Product.slug)
            .where(active, (Product.hallmark_details.is_(None)) | (Product.hallmark_details == ""))
            .order_by(Product.slug)
        )
    )
    report.unpriced = list(
        db.scalars(select(Product.slug).where(active, Product.price_from.is_(None)))
    )
    return report
