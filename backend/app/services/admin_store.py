"""Store administration rules: discounts, coupons, shipping, content, settings and staff roles.

Every function adds an audit-log entry; callers commit. Anything that can change a price
(discounts, tax settings) refreshes the listing price cache.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.models import (
    Category,
    Collection,
    ContentPage,
    Coupon,
    CouponRedemption,
    Discount,
    Product,
    ShippingMethod,
    ShippingZone,
    User,
)
from app.schemas.admin_store import (
    ContentPageIn,
    CouponCreateIn,
    CouponUpdateIn,
    DiscountIn,
    ShippingMethodIn,
    ShippingZoneIn,
)
from app.services import audit, store_settings
from app.services.auth import revoke_all_sessions
from app.services.catalogue import refresh_price_cache


def _record(
    db: Session,
    actor: User,
    action: str,
    entity: str,
    entity_id: object,
    changes: dict[str, Any],
    ip: str | None,
) -> None:
    audit.record(
        db,
        actor=actor,
        action=action,
        entity_type=entity,
        entity_id=str(entity_id),
        changes=changes,
        ip_address=ip,
    )


# --------------------------------------------------------------------------------------------
# Discounts
# --------------------------------------------------------------------------------------------


def scope_name(db: Session, scope: str, scope_id: uuid.UUID | None) -> str | None:
    model: Any = {"category": Category, "collection": Collection, "product": Product}.get(scope)
    if model is None or scope_id is None:
        return None
    row = db.get(model, scope_id)
    return row.name if row is not None else None


def save_discount(
    db: Session, actor: User, data: DiscountIn, discount: Discount | None, ip: str | None
) -> Discount:
    if data.scope != "all" and scope_name(db, data.scope, data.scope_id) is None:
        raise ValidationFailed({"scope_id": f"Choose an existing {data.scope}."})
    created = discount is None
    if discount is None:
        discount = Discount()
        db.add(discount)
    for field in (
        "name",
        "kind",
        "value",
        "scope",
        "scope_id",
        "starts_at",
        "ends_at",
        "is_active",
    ):
        setattr(discount, field, getattr(data, field))
    db.flush()
    _record(
        db,
        actor,
        "discount.create" if created else "discount.update",
        "discount",
        discount.id,
        data.model_dump(mode="json"),
        ip,
    )
    refresh_price_cache(db)
    return discount


# --------------------------------------------------------------------------------------------
# Coupons
# --------------------------------------------------------------------------------------------


def coupon_usage(db: Session, coupon_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, int]]:
    """{coupon id: (redeemed, reserved)}"""
    usage: dict[uuid.UUID, tuple[int, int]] = {}
    if not coupon_ids:
        return usage
    rows = db.execute(
        select(CouponRedemption.coupon_id, CouponRedemption.status, func.count())
        .where(CouponRedemption.coupon_id.in_(coupon_ids))
        .group_by(CouponRedemption.coupon_id, CouponRedemption.status)
    ).all()
    for coupon_id, status, count in rows:
        redeemed, reserved = usage.get(coupon_id, (0, 0))
        if status == "redeemed":
            redeemed += count
        elif status == "reserved":
            reserved += count
        usage[coupon_id] = (redeemed, reserved)
    return usage


COUPON_FIELDS = (
    "description",
    "kind",
    "value",
    "max_discount_amount",
    "min_order_amount",
    "starts_at",
    "ends_at",
    "usage_limit_total",
    "usage_limit_per_customer",
    "is_active",
)


def create_coupon(db: Session, actor: User, data: CouponCreateIn, ip: str | None) -> Coupon:
    if db.scalar(select(Coupon.id).where(Coupon.code == data.code)) is not None:
        raise ValidationFailed({"code": "This code already exists."})
    coupon = Coupon(code=data.code, **{f: getattr(data, f) for f in COUPON_FIELDS})
    db.add(coupon)
    db.flush()
    _record(db, actor, "coupon.create", "coupon", coupon.code, data.model_dump(mode="json"), ip)
    return coupon


def update_coupon(
    db: Session, actor: User, coupon: Coupon, data: CouponUpdateIn, ip: str | None
) -> Coupon:
    """The code itself can't change (customers and past orders refer to it)."""
    for f in COUPON_FIELDS:
        setattr(coupon, f, getattr(data, f))
    db.flush()
    _record(db, actor, "coupon.update", "coupon", coupon.code, data.model_dump(mode="json"), ip)
    return coupon


# --------------------------------------------------------------------------------------------
# Shipping
# --------------------------------------------------------------------------------------------


def save_method(
    db: Session, actor: User, data: ShippingMethodIn, method: ShippingMethod | None, ip: str | None
) -> ShippingMethod:
    clash = select(ShippingMethod.id).where(ShippingMethod.code == data.code)
    if method is not None:
        clash = clash.where(ShippingMethod.id != method.id)
    if db.scalar(clash) is not None:
        raise ValidationFailed({"code": "Another delivery method uses this code."})
    created = method is None
    if method is None:
        method = ShippingMethod()
        db.add(method)
    for f in (
        "code",
        "name",
        "description",
        "fee",
        "free_above",
        "min_days",
        "max_days",
        "is_active",
        "sort_order",
    ):
        setattr(method, f, getattr(data, f))
    db.flush()
    if not created and not data.is_active:
        active = db.scalar(
            select(func.count()).select_from(ShippingMethod).where(ShippingMethod.is_active)
        )
        if not active:
            raise Conflict(
                "At least one delivery method must stay active, or customers can't check out.",
                code="LAST_SHIPPING_METHOD",
            )
    _record(
        db,
        actor,
        "shipping_method.create" if created else "shipping_method.update",
        "shipping_method",
        method.code,
        data.model_dump(mode="json"),
        ip,
    )
    return method


def save_zone(
    db: Session, actor: User, data: ShippingZoneIn, zone: ShippingZone | None, ip: str | None
) -> ShippingZone:
    created = zone is None
    if zone is None:
        zone = ShippingZone()
        db.add(zone)
    for f in ("name", "pincode_prefixes", "extra_days", "is_active"):
        setattr(zone, f, getattr(data, f))
    db.flush()
    _record(
        db,
        actor,
        "shipping_zone.create" if created else "shipping_zone.update",
        "shipping_zone",
        zone.id,
        data.model_dump(mode="json"),
        ip,
    )
    return zone


def delete_zone(db: Session, actor: User, zone: ShippingZone, ip: str | None) -> None:
    db.delete(zone)
    _record(db, actor, "shipping_zone.delete", "shipping_zone", zone.id, {"name": zone.name}, ip)


# --------------------------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------------------------


def save_page(
    db: Session, actor: User, page: ContentPage, data: ContentPageIn, ip: str | None
) -> ContentPage:
    for f in ("title", "summary", "body_markdown", "is_draft_template"):
        setattr(page, f, getattr(data, f))
    page.updated_by = actor.id
    db.flush()
    _record(
        db,
        actor,
        "content.update",
        "content_page",
        page.slug,
        {
            "title": data.title,
            "is_draft_template": data.is_draft_template,
            "length": len(data.body_markdown),
        },
        ip,
    )
    return page


# --------------------------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------------------------


def save_settings(
    db: Session, actor: User, group: str, values: dict[str, Any], ip: str | None
) -> dict[str, Any]:
    before = store_settings.get_group(db, group)
    store_settings.set_group(db, group, values, updated_by=actor.id)
    db.flush()
    after = store_settings.get_group(db, group)
    _record(
        db,
        actor,
        f"settings.{group}",
        "settings",
        group,
        {k: [before.get(k), after.get(k)] for k in after if before.get(k) != after.get(k)},
        ip,
    )
    if group == "tax":
        refresh_price_cache(db)
    return after


# --------------------------------------------------------------------------------------------
# Staff users (admin only)
# --------------------------------------------------------------------------------------------


def _admins_left(db: Session, excluding: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == "admin", User.is_active, User.id != excluding)
        )
        or 0
    )


def set_role(db: Session, actor: User, user: User, role: str, ip: str | None) -> User:
    if user.id == actor.id:
        raise Conflict("You can't change your own role.", code="SELF_CHANGE")
    if user.role == "admin" and role != "admin" and _admins_left(db, user.id) == 0:
        raise Conflict("The store needs at least one active admin.", code="LAST_ADMIN")
    previous = user.role
    user.role = role
    # Permissions come from the role in the database on every request; signing out makes the
    # change obvious to the person and drops any cached admin screens.
    revoke_all_sessions(db, user.id, "role_changed")
    _record(
        db,
        actor,
        "user.role",
        "user",
        user.id,
        {"email": user.email, "from": previous, "to": role},
        ip,
    )
    return user


def set_active(db: Session, actor: User, user: User, active: bool, ip: str | None) -> User:
    if user.id == actor.id:
        raise Conflict("You can't deactivate your own account.", code="SELF_CHANGE")
    if not active and user.role == "admin" and _admins_left(db, user.id) == 0:
        raise Conflict("The store needs at least one active admin.", code="LAST_ADMIN")
    user.is_active = active
    if not active:
        revoke_all_sessions(db, user.id, "deactivated")
    _record(
        db,
        actor,
        "user.activate" if active else "user.deactivate",
        "user",
        user.id,
        {"email": user.email},
        ip,
    )
    return user


def find_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("User not found.")
    return user
