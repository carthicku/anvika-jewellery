"""Admin operations: dashboard, orders, inventory, gold rates, customers and the audit log.

Every route declares `require_permission(...)` (enforced by tests). Mutations are audited.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_gateway, get_request_meta, require_permission
from app.api.v1.routes.auth import send_emails_later
from app.core.config import Settings
from app.core.db import get_db
from app.core.errors import NotFound
from app.core.money import ZERO
from app.models import (
    Address,
    AuditLog,
    InventoryLevel,
    InventoryMovement,
    Order,
    PaymentAttempt,
    Product,
    ProductVariant,
    Refund,
    User,
)
from app.schemas.admin import (
    AdjustStockIn,
    AdminOrderEventOut,
    AdminOrderOut,
    AdminOrderRowOut,
    AdminRefundOut,
    AuditLogOut,
    BestSellerOut,
    CreateRateIn,
    CustomerDetailOut,
    CustomerRowOut,
    DashboardOut,
    GoldRateOut,
    GoldRatesOut,
    InventoryRowOut,
    LowStockOut,
    MovementOut,
    NoteIn,
    OrderStatusAction,
    PaymentAttemptOut,
    PriceImpactOut,
    RatePreviewIn,
    RatePreviewOut,
    RateStatusOut,
    ReasonIn,
    RefundIn,
    ResolveReviewIn,
    ShipIn,
    ThresholdIn,
)
from app.schemas.common import Page
from app.services import admin_orders, audit, dashboard, gold_rates, inventory, orders
from app.services.account import address_out
from app.services.auth import RequestMeta
from app.services.catalogue import page_count
from app.services.payment_gateway import PaymentGateway

router = APIRouter(prefix="/admin", tags=["admin"])

PageNo = Annotated[int, Query(ge=1, le=10_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _row(order: Order) -> AdminOrderRowOut:
    return AdminOrderRowOut(
        reference=order.reference,
        created_at=order.created_at,
        customer_name=order.customer_name,
        email=order.email,
        status=order.status,
        status_label=orders.STATUS_LABELS[order.status],
        payment_status=order.payment_status,
        payment_status_label=orders.PAYMENT_LABELS[order.payment_status],
        grand_total=order.grand_total,
        item_count=sum(i.quantity for i in order.items),
    )


def _rate_status(status: gold_rates.RateStatus) -> RateStatusOut:
    return RateStatusOut(
        purity=status.purity,
        rate_per_gram=status.rate.rate_per_gram if status.rate else None,
        effective_from=status.rate.effective_from if status.rate else None,
        source_note=status.rate.source_note if status.rate else None,
        age_hours=status.age_hours,
        stale=status.stale,
    )


# --------------------------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------------------------


@router.get(
    "/dashboard",
    response_model=DashboardOut,
    dependencies=[Depends(require_permission("dashboard:view"))],
)
def get_dashboard(
    response: Response,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    db: Session = Depends(get_db),
) -> DashboardOut:
    _no_store(response)
    d = dashboard.build(db, date_from, date_to)
    return DashboardOut(
        date_from=d.date_from,
        date_to=d.date_to,
        paid_orders=d.paid_orders,
        paid_revenue=d.paid_revenue,
        refunded=d.refunded,
        paid_orders_today=d.paid_orders_today,
        pending_payment=d.pending_payment,
        payment_review=d.payment_review,
        to_fulfil=d.to_fulfil,
        recent_orders=[_row(o) for o in d.recent],
        review_orders=[_row(o) for o in d.review_orders],
        low_stock=[LowStockOut(**r.__dict__) for r in d.low_stock],
        best_sellers=[BestSellerOut(**b.__dict__) for b in d.best_sellers],
        gold_rates=[_rate_status(r) for r in d.rates],
    )


# --------------------------------------------------------------------------------------------
# Orders
# --------------------------------------------------------------------------------------------


@router.get(
    "/orders",
    response_model=Page[AdminOrderRowOut],
    dependencies=[Depends(require_permission("orders:write"))],
)
def list_orders(
    response: Response,
    status: Annotated[str | None, Query(max_length=20)] = None,
    payment_status: Annotated[str | None, Query(max_length=20)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    page: PageNo = 1,
    page_size: PageSize = 25,
    db: Session = Depends(get_db),
) -> Page[AdminOrderRowOut]:
    _no_store(response)
    rows, total = admin_orders.list_orders(
        db,
        admin_orders.OrderFilters(status, payment_status, q, date_from, date_to),
        page,
        page_size,
    )
    return Page(
        items=[_row(o) for o in rows],
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


def _admin_order(db: Session, order: Order) -> AdminOrderOut:
    attempts = db.scalars(
        select(PaymentAttempt)
        .where(PaymentAttempt.order_id == order.id)
        .order_by(PaymentAttempt.created_at)
    ).all()
    refunds = db.scalars(
        select(Refund).where(Refund.order_id == order.id).order_by(Refund.created_at)
    ).all()
    return AdminOrderOut(
        order=orders.order_view(db, order),
        customer_id=str(order.user_id) if order.user_id else None,
        events=[
            AdminOrderEventOut(
                kind=e.kind,
                title=orders.EVENT_TITLES.get(e.kind, e.kind.replace("_", " ").capitalize()),
                note=e.note,
                from_status=e.from_status,
                to_status=e.to_status,
                actor_type=e.actor_type,
                customer_visible=e.customer_visible,
                created_at=e.created_at,
            )
            for e in admin_orders.events(db, order)
        ],
        payment_attempts=[
            PaymentAttemptOut(
                provider=a.provider,
                provider_order_id=a.provider_order_id,
                provider_payment_id=a.provider_payment_id,
                amount_paise=a.amount_paise,
                status=a.status,
                method=a.method,
                error_description=a.error_description,
                created_at=a.created_at,
            )
            for a in attempts
        ],
        refunds=[
            AdminRefundOut(
                id=str(r.id),
                amount=r.amount,
                status=r.status,
                reason=r.reason,
                provider_refund_id=r.provider_refund_id,
                created_at=r.created_at,
            )
            for r in refunds
        ],
        refundable=orders.refundable_amount(db, order) if order.paid_at else ZERO,
        allowed_actions=admin_orders.allowed_actions(db, order),
    )


@router.get(
    "/orders/{reference}",
    response_model=AdminOrderOut,
    dependencies=[Depends(require_permission("orders:write"))],
)
def get_order(reference: str, response: Response, db: Session = Depends(get_db)) -> AdminOrderOut:
    _no_store(response)
    return _admin_order(db, admin_orders.find(db, reference))


def _finish(db: Session, request: Request, tasks: BackgroundTasks, order: Order) -> AdminOrderOut:
    db.commit()
    out = _admin_order(db, order)
    db.commit()
    send_emails_later(request, tasks)
    return out


@router.post("/orders/{reference}/status", response_model=AdminOrderOut)
def change_status(
    reference: str,
    data: OrderStatusAction,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("orders:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminOrderOut:
    order = admin_orders.find(db, reference, lock=True)
    if data.action == "start_processing":
        admin_orders.start_processing(db, user, order, meta.ip)
    else:
        admin_orders.mark_delivered(db, user, order, meta.ip)
    return _finish(db, request, tasks, order)


@router.post("/orders/{reference}/shipments", response_model=AdminOrderOut)
def ship_order(
    reference: str,
    data: ShipIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_permission("orders:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminOrderOut:
    order = admin_orders.find(db, reference, lock=True)
    admin_orders.ship(
        db,
        settings,
        user,
        order,
        carrier=data.carrier,
        tracking_number=data.tracking_number,
        tracking_url=data.tracking_url,
        ip=meta.ip,
    )
    return _finish(db, request, tasks, order)


@router.post("/orders/{reference}/cancel", response_model=AdminOrderOut)
def cancel_order(
    reference: str,
    data: ReasonIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_permission("orders:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminOrderOut:
    order = admin_orders.find(db, reference, lock=True)
    admin_orders.cancel(db, settings, user, order, data.reason, meta.ip)
    return _finish(db, request, tasks, order)


@router.post("/orders/{reference}/notes", response_model=AdminOrderOut)
def add_note(
    reference: str,
    data: NoteIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("orders:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminOrderOut:
    order = admin_orders.find(db, reference, lock=True)
    admin_orders.add_note(db, user, order, data.note, meta.ip)
    return _finish(db, request, tasks, order)


@router.post("/orders/{reference}/review", response_model=AdminOrderOut)
def resolve_review(
    reference: str,
    data: ResolveReviewIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_permission("orders:refund")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminOrderOut:
    order = admin_orders.find(db, reference, lock=True)
    admin_orders.resolve_review(db, settings, user, order, data.decision, data.note, meta.ip)
    return _finish(db, request, tasks, order)


@router.post("/orders/{reference}/refunds", response_model=AdminOrderOut)
def request_refund(
    reference: str,
    data: RefundIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("orders:refund")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminOrderOut:
    """Record a (partial) refund request; it is sent to the provider with the execute action."""
    order = admin_orders.find(db, reference, lock=True)
    if order.paid_at is None:
        raise NotFound("This order has no payment to refund.")
    refund = admin_orders.request_refund(db, user, order, data.amount, data.reason)
    audit.record(
        db,
        actor=user,
        action="order.refund_requested",
        entity_type="order",
        entity_id=order.reference,
        changes={"refund_id": str(refund.id), "amount": str(refund.amount), "reason": data.reason},
        ip_address=meta.ip,
    )
    return _finish(db, request, tasks, order)


@router.post("/orders/{reference}/refunds/{refund_id}/execute", response_model=AdminOrderOut)
def execute_refund(
    reference: str,
    refund_id: uuid.UUID,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    gateway: PaymentGateway = Depends(get_gateway),
    user: User = Depends(require_permission("orders:refund")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminOrderOut:
    """Send a requested refund to the payment provider (real money with live keys)."""
    order = admin_orders.find(db, reference, lock=True)
    admin_orders.execute_refund(db, settings, gateway, user, order, refund_id, meta.ip)
    return _finish(db, request, tasks, order)


# --------------------------------------------------------------------------------------------
# Inventory
# --------------------------------------------------------------------------------------------


def _inventory_row(
    level: InventoryLevel, variant: ProductVariant, product: Product
) -> InventoryRowOut:
    return InventoryRowOut(
        variant_id=str(variant.id),
        sku=variant.sku,
        product_name=product.name,
        product_slug=product.slug,
        variant_label=variant.label,
        product_status=product.status,
        on_hand=level.on_hand,
        reserved=level.reserved,
        available=level.available,
        low_stock_threshold=level.low_stock_threshold,
        stock_status=inventory.stock_status(level),
    )


@router.get(
    "/inventory",
    response_model=Page[InventoryRowOut],
    dependencies=[Depends(require_permission("inventory:write"))],
)
def list_inventory(
    response: Response,
    q: Annotated[str | None, Query(max_length=100)] = None,
    low_only: bool = False,
    page: PageNo = 1,
    page_size: PageSize = 50,
    db: Session = Depends(get_db),
) -> Page[InventoryRowOut]:
    _no_store(response)
    stmt = (
        select(InventoryLevel, ProductVariant, Product)
        .join(ProductVariant, ProductVariant.id == InventoryLevel.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(Product.status != "archived")
    )
    if q:
        like = f"%{q.strip().replace('%', '').replace('_', '')}%"
        stmt = stmt.where(or_(Product.name.ilike(like), ProductVariant.sku.ilike(like)))
    if low_only:
        stmt = stmt.where(
            InventoryLevel.on_hand - InventoryLevel.reserved <= InventoryLevel.low_stock_threshold
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(Product.name, ProductVariant.sku)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[_inventory_row(*row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


def _variant_with_level(db: Session, variant_id: uuid.UUID) -> tuple[ProductVariant, Product]:
    row = db.execute(
        select(ProductVariant, Product)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(ProductVariant.id == variant_id)
    ).first()
    if row is None:
        raise NotFound("Variant not found.")
    return row[0], row[1]


@router.post("/inventory/{variant_id}/adjust", response_model=InventoryRowOut)
def adjust_stock(
    variant_id: uuid.UUID,
    data: AdjustStockIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> InventoryRowOut:
    variant, product = _variant_with_level(db, variant_id)
    level = inventory.adjust(db, variant.id, data.delta, note=data.note, actor_user_id=user.id)
    audit.record(
        db,
        actor=user,
        action="inventory.adjust",
        entity_type="variant",
        entity_id=variant.sku,
        changes={"delta": data.delta, "note": data.note, "on_hand": level.on_hand},
        ip_address=meta.ip,
    )
    db.commit()
    return _inventory_row(level, variant, product)


@router.put("/inventory/{variant_id}/threshold", response_model=InventoryRowOut)
def set_threshold(
    variant_id: uuid.UUID,
    data: ThresholdIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> InventoryRowOut:
    variant, product = _variant_with_level(db, variant_id)
    level = db.get(InventoryLevel, variant.id, with_for_update=True)
    if level is None:
        raise NotFound("No stock record for this variant.")
    previous = level.low_stock_threshold
    level.low_stock_threshold = data.low_stock_threshold
    audit.record(
        db,
        actor=user,
        action="inventory.threshold",
        entity_type="variant",
        entity_id=variant.sku,
        changes={"from": previous, "to": data.low_stock_threshold},
        ip_address=meta.ip,
    )
    db.commit()
    return _inventory_row(level, variant, product)


@router.get(
    "/inventory/movements",
    response_model=Page[MovementOut],
    dependencies=[Depends(require_permission("inventory:write"))],
)
def list_movements(
    response: Response,
    variant_id: uuid.UUID | None = None,
    page: PageNo = 1,
    page_size: PageSize = 50,
    db: Session = Depends(get_db),
) -> Page[MovementOut]:
    _no_store(response)
    stmt = (
        select(InventoryMovement, ProductVariant.sku, Product.name, Order.reference, User.email)
        .join(ProductVariant, ProductVariant.id == InventoryMovement.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .outerjoin(Order, Order.id == InventoryMovement.order_id)
        .outerjoin(User, User.id == InventoryMovement.actor_user_id)
    )
    if variant_id:
        stmt = stmt.where(InventoryMovement.variant_id == variant_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(InventoryMovement.created_at.desc(), InventoryMovement.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[
            MovementOut(
                created_at=m.created_at,
                sku=sku,
                product_name=name,
                delta_on_hand=m.delta_on_hand,
                delta_reserved=m.delta_reserved,
                reason=m.reason,
                note=m.note,
                order_reference=reference,
                actor_email=email,
            )
            for m, sku, name, reference, email in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


# --------------------------------------------------------------------------------------------
# Gold rates
# --------------------------------------------------------------------------------------------


@router.get(
    "/gold-rates",
    response_model=GoldRatesOut,
    dependencies=[Depends(require_permission("pricing:write"))],
)
def list_gold_rates(response: Response, db: Session = Depends(get_db)) -> GoldRatesOut:
    _no_store(response)
    max_change, stale_after = gold_rates.policy(db)
    return GoldRatesOut(
        current=[_rate_status(s) for s in gold_rates.current_status(db)],
        history=[
            GoldRateOut(
                id=str(r.id),
                purity=r.purity,
                rate_per_gram=r.rate_per_gram,
                effective_from=r.effective_from,
                source_note=r.source_note,
                created_at=r.created_at,
            )
            for r in gold_rates.history(db)
        ],
        max_change_percent=max_change,
        stale_after_hours=stale_after,
    )


def _preview_out(p: gold_rates.RatePreview) -> RatePreviewOut:
    return RatePreviewOut(
        purity=p.purity,
        current_rate=p.current_rate,
        new_rate=p.new_rate,
        change_percent=p.change_percent,
        needs_confirmation=p.needs_confirmation,
        max_change_percent=p.max_change_percent,
        impacts=[PriceImpactOut(**i.__dict__) for i in p.impacts],
    )


@router.post(
    "/gold-rates/preview",
    response_model=RatePreviewOut,
    dependencies=[Depends(require_permission("pricing:write"))],
)
def preview_gold_rate(data: RatePreviewIn, db: Session = Depends(get_db)) -> RatePreviewOut:
    """Old vs new price of every affected piece. Saves nothing."""
    return _preview_out(gold_rates.preview(db, data.purity, data.rate_per_gram))


@router.post("/gold-rates", response_model=GoldRateOut, status_code=201)
def create_gold_rate(
    data: CreateRateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("pricing:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> GoldRateOut:
    rate = gold_rates.create_rate(
        db,
        user,
        purity=data.purity,
        rate_per_gram=data.rate_per_gram,
        source_note=data.source_note,
        effective_from=data.effective_from,
        confirm_large_change=data.confirm_large_change,
        ip_address=meta.ip,
    )
    db.commit()
    return GoldRateOut(
        id=str(rate.id),
        purity=data.purity,
        rate_per_gram=rate.rate_per_gram,
        effective_from=rate.effective_from,
        source_note=rate.source_note,
        created_at=rate.created_at,
    )


# --------------------------------------------------------------------------------------------
# Customers
# --------------------------------------------------------------------------------------------


def _customer_rows(db: Session, users: list[User]) -> list[CustomerRowOut]:
    ids = [u.id for u in users]
    stats: dict[uuid.UUID, tuple[int, Decimal]] = {}
    if ids:
        for user_id, count, paid in db.execute(
            select(
                Order.user_id,
                func.count(),
                func.coalesce(
                    func.sum(Order.grand_total).filter(
                        Order.payment_status.in_(dashboard.PAID_STATES)
                    ),
                    ZERO,
                ),
            )
            .where(Order.user_id.in_(ids))
            .group_by(Order.user_id)
        ):
            if user_id is not None:
                stats[user_id] = (count, paid)
    return [
        CustomerRowOut(
            id=str(u.id),
            full_name=u.full_name,
            email=u.email,
            phone=u.phone,
            created_at=u.created_at,
            is_active=u.is_active,
            email_verified=u.email_verified_at is not None,
            order_count=stats.get(u.id, (0, ZERO))[0],
            paid_total=stats.get(u.id, (0, ZERO))[1],
        )
        for u in users
    ]


@router.get(
    "/customers",
    response_model=Page[CustomerRowOut],
    dependencies=[Depends(require_permission("customers:view"))],
)
def list_customers(
    response: Response,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: PageNo = 1,
    page_size: PageSize = 25,
    db: Session = Depends(get_db),
) -> Page[CustomerRowOut]:
    _no_store(response)
    stmt = select(User).where(User.role == "customer")
    if q:
        like = f"%{q.strip().replace('%', '').replace('_', '')}%"
        stmt = stmt.where(
            or_(User.email.ilike(like), User.full_name.ilike(like), User.phone.ilike(like))
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = list(
        db.scalars(
            stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
    )
    return Page(
        items=_customer_rows(db, users),
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerDetailOut,
    dependencies=[Depends(require_permission("customers:view"))],
)
def get_customer(
    customer_id: uuid.UUID, response: Response, db: Session = Depends(get_db)
) -> CustomerDetailOut:
    _no_store(response)
    user = db.get(User, customer_id)
    if user is None or user.role != "customer":
        raise NotFound("Customer not found.")
    addresses = db.scalars(
        select(Address).where(Address.user_id == user.id).order_by(Address.created_at)
    ).all()
    return CustomerDetailOut(
        customer=_customer_rows(db, [user])[0],
        addresses=[address_out(a) for a in addresses],
        orders=orders.list_orders(db, user, 1, 50).items,
    )


# --------------------------------------------------------------------------------------------
# Audit log
# --------------------------------------------------------------------------------------------


@router.get(
    "/audit-logs",
    response_model=Page[AuditLogOut],
    dependencies=[Depends(require_permission("audit:view"))],
)
def list_audit_logs(
    response: Response,
    entity_type: Annotated[str | None, Query(max_length=40)] = None,
    entity_id: Annotated[str | None, Query(max_length=64)] = None,
    action: Annotated[str | None, Query(max_length=64)] = None,
    page: PageNo = 1,
    page_size: PageSize = 50,
    db: Session = Depends(get_db),
) -> Page[AuditLogOut]:
    _no_store(response)
    stmt = select(AuditLog, User.email).outerjoin(User, User.id == AuditLog.actor_user_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(AuditLog.created_at.desc(), AuditLog.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[
            AuditLogOut(
                id=str(log.id),
                created_at=log.created_at,
                actor_email=email,
                actor_role=log.actor_role,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                changes=log.changes,
                ip_address=log.ip_address,
            )
            for log, email in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )
