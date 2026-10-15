"""Admin: discounts, coupons, shipping, content pages, enquiries, newsletter, settings and staff.
Every route declares its permission; mutations are audited in app.services.admin_store."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_request_meta, require_permission
from app.core.db import get_db
from app.core.errors import NotFound
from app.core.time import utcnow
from app.models import (
    ContactEnquiry,
    ContentPage,
    Coupon,
    Discount,
    NewsletterSubscriber,
    ShippingMethod,
    ShippingZone,
    User,
)
from app.schemas.admin_store import (
    ActiveIn,
    AdminContentPageOut,
    AnnouncementIn,
    ContentPageIn,
    CouponCreateIn,
    CouponOut,
    CouponUpdateIn,
    DiscountIn,
    DiscountOut,
    EnquiryOut,
    EnquiryStatusIn,
    PricingPolicyIn,
    PromoteIn,
    RoleIn,
    SettingsOut,
    ShippingMethodIn,
    ShippingMethodOut,
    ShippingZoneIn,
    ShippingZoneOut,
    StaffUserOut,
    StoreSettingsIn,
    SubscriberOut,
    TaxIn,
)
from app.schemas.common import OkOut, Page
from app.services import admin_store as service
from app.services import audit, store_settings
from app.services.auth import RequestMeta, normalise_email
from app.services.catalogue import page_count

router = APIRouter(prefix="/admin", tags=["admin-store"])

PageNo = Annotated[int, Query(ge=1, le=10_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]


# --------------------------------------------------------------------------------------------
# Discounts
# --------------------------------------------------------------------------------------------


def _discount_out(db: Session, d: Discount) -> DiscountOut:
    now = utcnow()
    return DiscountOut(
        id=str(d.id),
        name=d.name,
        kind=d.kind,
        value=d.value,
        scope=d.scope,
        scope_id=str(d.scope_id) if d.scope_id else None,
        scope_name=service.scope_name(db, d.scope, d.scope_id),
        starts_at=d.starts_at,
        ends_at=d.ends_at,
        is_active=d.is_active,
        running_now=d.is_active and d.starts_at <= now and (d.ends_at is None or d.ends_at > now),
    )


@router.get(
    "/discounts",
    response_model=list[DiscountOut],
    dependencies=[Depends(require_permission("promotions:write"))],
)
def list_discounts(db: Session = Depends(get_db)) -> list[DiscountOut]:
    rows = db.scalars(select(Discount).order_by(Discount.starts_at.desc())).all()
    return [_discount_out(db, d) for d in rows]


@router.post("/discounts", response_model=DiscountOut, status_code=201)
def create_discount(
    data: DiscountIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("promotions:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> DiscountOut:
    discount = service.save_discount(db, user, data, None, meta.ip)
    db.commit()
    return _discount_out(db, discount)


@router.put("/discounts/{discount_id}", response_model=DiscountOut)
def update_discount(
    discount_id: uuid.UUID,
    data: DiscountIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("promotions:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> DiscountOut:
    discount = db.get(Discount, discount_id)
    if discount is None:
        raise NotFound("Discount not found.")
    service.save_discount(db, user, data, discount, meta.ip)
    db.commit()
    return _discount_out(db, discount)


# --------------------------------------------------------------------------------------------
# Coupons
# --------------------------------------------------------------------------------------------


def _coupon_rows(db: Session, coupons: list[Coupon]) -> list[CouponOut]:
    usage = service.coupon_usage(db, [c.id for c in coupons])
    return [
        CouponOut(
            id=str(c.id),
            code=c.code,
            description=c.description,
            kind=c.kind,
            value=c.value,
            max_discount_amount=c.max_discount_amount,
            min_order_amount=c.min_order_amount,
            starts_at=c.starts_at,
            ends_at=c.ends_at,
            usage_limit_total=c.usage_limit_total,
            usage_limit_per_customer=c.usage_limit_per_customer,
            is_active=c.is_active,
            is_sample=c.is_sample,
            times_used=usage.get(c.id, (0, 0))[0],
            times_reserved=usage.get(c.id, (0, 0))[1],
        )
        for c in coupons
    ]


@router.get(
    "/coupons",
    response_model=list[CouponOut],
    dependencies=[Depends(require_permission("promotions:write"))],
)
def list_coupons(db: Session = Depends(get_db)) -> list[CouponOut]:
    return _coupon_rows(db, list(db.scalars(select(Coupon).order_by(Coupon.created_at.desc()))))


@router.post("/coupons", response_model=CouponOut, status_code=201)
def create_coupon(
    data: CouponCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("promotions:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> CouponOut:
    coupon = service.create_coupon(db, user, data, meta.ip)
    db.commit()
    return _coupon_rows(db, [coupon])[0]


@router.put("/coupons/{coupon_id}", response_model=CouponOut)
def update_coupon(
    coupon_id: uuid.UUID,
    data: CouponUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("promotions:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> CouponOut:
    coupon = db.get(Coupon, coupon_id)
    if coupon is None:
        raise NotFound("Coupon not found.")
    service.update_coupon(db, user, coupon, data, meta.ip)
    db.commit()
    return _coupon_rows(db, [coupon])[0]


# --------------------------------------------------------------------------------------------
# Shipping
# --------------------------------------------------------------------------------------------


def _method_out(m: ShippingMethod) -> ShippingMethodOut:
    return ShippingMethodOut(
        id=str(m.id),
        code=m.code,
        name=m.name,
        description=m.description,
        fee=m.fee,
        free_above=m.free_above,
        min_days=m.min_days,
        max_days=m.max_days,
        is_active=m.is_active,
        sort_order=m.sort_order,
    )


def _zone_out(z: ShippingZone) -> ShippingZoneOut:
    return ShippingZoneOut(
        id=str(z.id),
        name=z.name,
        pincode_prefixes=list(z.pincode_prefixes),
        extra_days=z.extra_days,
        is_active=z.is_active,
    )


@router.get(
    "/shipping/methods",
    response_model=list[ShippingMethodOut],
    dependencies=[Depends(require_permission("settings:write"))],
)
def list_methods(db: Session = Depends(get_db)) -> list[ShippingMethodOut]:
    rows = db.scalars(select(ShippingMethod).order_by(ShippingMethod.sort_order)).all()
    return [_method_out(m) for m in rows]


@router.post("/shipping/methods", response_model=ShippingMethodOut, status_code=201)
def create_method(
    data: ShippingMethodIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> ShippingMethodOut:
    method = service.save_method(db, user, data, None, meta.ip)
    db.commit()
    return _method_out(method)


@router.put("/shipping/methods/{method_id}", response_model=ShippingMethodOut)
def update_method(
    method_id: uuid.UUID,
    data: ShippingMethodIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> ShippingMethodOut:
    method = db.get(ShippingMethod, method_id)
    if method is None:
        raise NotFound("Delivery method not found.")
    service.save_method(db, user, data, method, meta.ip)
    db.commit()
    return _method_out(method)


@router.get(
    "/shipping/zones",
    response_model=list[ShippingZoneOut],
    dependencies=[Depends(require_permission("settings:write"))],
)
def list_zones(db: Session = Depends(get_db)) -> list[ShippingZoneOut]:
    return [_zone_out(z) for z in db.scalars(select(ShippingZone).order_by(ShippingZone.name))]


@router.post("/shipping/zones", response_model=ShippingZoneOut, status_code=201)
def create_zone(
    data: ShippingZoneIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> ShippingZoneOut:
    zone = service.save_zone(db, user, data, None, meta.ip)
    db.commit()
    return _zone_out(zone)


def _zone(db: Session, zone_id: uuid.UUID) -> ShippingZone:
    zone = db.get(ShippingZone, zone_id)
    if zone is None:
        raise NotFound("Zone not found.")
    return zone


@router.put("/shipping/zones/{zone_id}", response_model=ShippingZoneOut)
def update_zone(
    zone_id: uuid.UUID,
    data: ShippingZoneIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> ShippingZoneOut:
    zone = service.save_zone(db, user, data, _zone(db, zone_id), meta.ip)
    db.commit()
    return _zone_out(zone)


@router.delete("/shipping/zones/{zone_id}", response_model=OkOut)
def delete_zone(
    zone_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> OkOut:
    service.delete_zone(db, user, _zone(db, zone_id), meta.ip)
    db.commit()
    return OkOut(message="Zone deleted.")


# --------------------------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------------------------


def _page_out(p: ContentPage) -> AdminContentPageOut:
    return AdminContentPageOut(
        slug=p.slug,
        title=p.title,
        summary=p.summary,
        body_markdown=p.body_markdown,
        is_draft_template=p.is_draft_template,
        updated_at=p.updated_at,
    )


@router.get(
    "/content",
    response_model=list[AdminContentPageOut],
    dependencies=[Depends(require_permission("content:write"))],
)
def list_pages(db: Session = Depends(get_db)) -> list[AdminContentPageOut]:
    return [_page_out(p) for p in db.scalars(select(ContentPage).order_by(ContentPage.title))]


def _page(db: Session, slug: str) -> ContentPage:
    page = db.scalar(select(ContentPage).where(ContentPage.slug == slug))
    if page is None:
        raise NotFound("Page not found.")
    return page


@router.get(
    "/content/{slug}",
    response_model=AdminContentPageOut,
    dependencies=[Depends(require_permission("content:write"))],
)
def get_page(slug: str, db: Session = Depends(get_db)) -> AdminContentPageOut:
    return _page_out(_page(db, slug))


@router.put("/content/{slug}", response_model=AdminContentPageOut)
def update_page(
    slug: str,
    data: ContentPageIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("content:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminContentPageOut:
    page = service.save_page(db, user, _page(db, slug), data, meta.ip)
    db.commit()
    return _page_out(page)


# --------------------------------------------------------------------------------------------
# Enquiries and newsletter
# --------------------------------------------------------------------------------------------


@router.get(
    "/enquiries",
    response_model=Page[EnquiryOut],
    dependencies=[Depends(require_permission("customers:view"))],
)
def list_enquiries(
    response: Response,
    status: Annotated[str | None, Query(max_length=16)] = None,
    page: PageNo = 1,
    page_size: PageSize = 25,
    db: Session = Depends(get_db),
) -> Page[EnquiryOut]:
    response.headers["Cache-Control"] = "no-store"
    stmt = select(ContactEnquiry)
    if status:
        stmt = stmt.where(ContactEnquiry.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ContactEnquiry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[
            EnquiryOut(
                id=str(e.id),
                name=e.name,
                email=e.email,
                phone=e.phone,
                subject=e.subject,
                message=e.message,
                status=e.status,
                created_at=e.created_at,
            )
            for e in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


@router.put("/enquiries/{enquiry_id}/status", response_model=OkOut)
def set_enquiry_status(
    enquiry_id: uuid.UUID,
    data: EnquiryStatusIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("customers:view")),
    meta: RequestMeta = Depends(get_request_meta),
) -> OkOut:
    enquiry = db.get(ContactEnquiry, enquiry_id)
    if enquiry is None:
        raise NotFound("Enquiry not found.")
    previous = enquiry.status
    enquiry.status = data.status
    audit.record(
        db,
        actor=user,
        action="enquiry.status",
        entity_type="enquiry",
        entity_id=enquiry.id,
        changes={"from": previous, "to": data.status},
        ip_address=meta.ip,
    )
    db.commit()
    return OkOut()


@router.get(
    "/newsletter",
    response_model=Page[SubscriberOut],
    dependencies=[Depends(require_permission("customers:view"))],
)
def list_subscribers(
    response: Response,
    status: Annotated[str | None, Query(max_length=16)] = None,
    page: PageNo = 1,
    page_size: PageSize = 50,
    db: Session = Depends(get_db),
) -> Page[SubscriberOut]:
    response.headers["Cache-Control"] = "no-store"
    stmt = select(NewsletterSubscriber)
    if status:
        stmt = stmt.where(NewsletterSubscriber.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(NewsletterSubscriber.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[
            SubscriberOut(
                email=s.email,
                status=s.status,
                source=s.source,
                consent_at=s.consent_at,
                unsubscribed_at=s.unsubscribed_at,
            )
            for s in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


# --------------------------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------------------------


def _settings(db: Session) -> SettingsOut:
    return SettingsOut(
        store=StoreSettingsIn.model_validate(store_settings.get_group(db, "store")),
        announcement=AnnouncementIn.model_validate(store_settings.get_group(db, "announcement")),
        tax=TaxIn.model_validate(store_settings.get_group(db, "tax")),
        pricing_policy=PricingPolicyIn.model_validate(
            store_settings.get_group(db, "pricing_policy")
        ),
    )


@router.get(
    "/settings",
    response_model=SettingsOut,
    dependencies=[Depends(require_permission("settings:write"))],
)
def get_settings(response: Response, db: Session = Depends(get_db)) -> SettingsOut:
    response.headers["Cache-Control"] = "no-store"
    return _settings(db)


def _save(
    db: Session, user: User, group: str, values: dict[str, Any], ip: str | None
) -> SettingsOut:
    service.save_settings(db, user, group, values, ip)
    db.commit()
    return _settings(db)


@router.put("/settings/store", response_model=SettingsOut)
def save_store(
    data: StoreSettingsIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> SettingsOut:
    return _save(db, user, "store", data.model_dump(), meta.ip)


@router.put("/settings/announcement", response_model=SettingsOut)
def save_announcement(
    data: AnnouncementIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> SettingsOut:
    return _save(db, user, "announcement", data.model_dump(), meta.ip)


@router.put("/settings/tax", response_model=SettingsOut)
def save_tax(
    data: TaxIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> SettingsOut:
    """GST rates per price component. Confirm with a tax professional before changing."""
    return _save(db, user, "tax", {k: str(v) for k, v in data.model_dump().items()}, meta.ip)


@router.put("/settings/pricing-policy", response_model=SettingsOut)
def save_pricing_policy(
    data: PricingPolicyIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> SettingsOut:
    values = data.model_dump()
    values["gold_rate_max_change_percent"] = str(data.gold_rate_max_change_percent)
    return _save(db, user, "pricing_policy", values, meta.ip)


# --------------------------------------------------------------------------------------------
# Staff users (admin only)
# --------------------------------------------------------------------------------------------


def _staff_out(u: User) -> StaffUserOut:
    return StaffUserOut(
        id=str(u.id),
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        is_active=u.is_active,
        last_login_at=u.last_login_at,
        created_at=u.created_at,
    )


@router.get(
    "/users",
    response_model=list[StaffUserOut],
    dependencies=[Depends(require_permission("users:manage"))],
)
def list_staff(db: Session = Depends(get_db)) -> list[StaffUserOut]:
    rows = db.scalars(
        select(User).where(User.role.in_(("staff", "admin"))).order_by(User.role, User.email)
    ).all()
    return [_staff_out(u) for u in rows]


@router.post("/users/promote", response_model=StaffUserOut)
def promote(
    data: PromoteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
    meta: RequestMeta = Depends(get_request_meta),
) -> StaffUserOut:
    """Give an existing account (they register first) staff or admin access."""
    target = db.scalar(select(User).where(User.email == normalise_email(data.email)))
    if target is None:
        raise NotFound("No account uses that email. Ask them to create an account first.")
    service.set_role(db, user, target, data.role, meta.ip)
    db.commit()
    return _staff_out(target)


@router.put("/users/{user_id}/role", response_model=StaffUserOut)
def change_role(
    user_id: uuid.UUID,
    data: RoleIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
    meta: RequestMeta = Depends(get_request_meta),
) -> StaffUserOut:
    target = service.set_role(db, user, service.find_user(db, user_id), data.role, meta.ip)
    db.commit()
    return _staff_out(target)


@router.put("/users/{user_id}/active", response_model=StaffUserOut)
def change_active(
    user_id: uuid.UUID,
    data: ActiveIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
    meta: RequestMeta = Depends(get_request_meta),
) -> StaffUserOut:
    target = service.set_active(db, user, service.find_user(db, user_id), data.is_active, meta.ip)
    db.commit()
    return _staff_out(target)
