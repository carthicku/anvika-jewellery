"""Customer profile, address book and wishlist. Every query is scoped to the signed-in user;
another customer's record is reported as NotFound (never Forbidden) so its existence is hidden."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.core.permissions import permissions_for
from app.models import Address, Product, User, UserSession, WishlistItem
from app.schemas.account import AddressIn, AddressOut, ProfileIn, SessionOut, UserOut
from app.schemas.catalogue import ProductCardOut
from app.services import catalogue

MAX_ADDRESSES = 20


def user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        email_verified=user.email_verified_at is not None,
        permissions=list(permissions_for(user.role)),
    )


def update_profile(user: User, data: ProfileIn) -> User:
    user.full_name = data.full_name.strip()
    user.phone = data.phone
    return user


def describe_device(user_agent: str | None) -> str:
    """A short, human description such as "Chrome on Windows" (best effort, no extra library)."""
    ua = (user_agent or "").lower()
    browser = next(
        (
            name
            for key, name in (
                ("edg/", "Edge"),
                ("chrome/", "Chrome"),
                ("firefox/", "Firefox"),
                ("safari/", "Safari"),
            )
            if key in ua
        ),
        "Browser",
    )
    system = next(
        (
            name
            for key, name in (
                ("android", "Android"),
                ("iphone", "iPhone"),
                ("ipad", "iPad"),
                ("windows", "Windows"),
                ("mac os", "macOS"),
                ("linux", "Linux"),
            )
            if key in ua
        ),
        "unknown device",
    )
    return f"{browser} on {system}"


def session_out(session: UserSession, current_id: uuid.UUID) -> SessionOut:
    return SessionOut(
        id=str(session.id),
        device=describe_device(session.user_agent),
        ip_address=session.ip_address,
        created_at=session.created_at,
        last_used_at=session.last_used_at,
        current=session.id == current_id,
    )


# --------------------------------------------------------------------------------------------
# Addresses
# --------------------------------------------------------------------------------------------


def address_out(address: Address) -> AddressOut:
    return AddressOut(
        id=str(address.id),
        label=address.label,
        full_name=address.full_name,
        phone=address.phone,
        line1=address.line1,
        line2=address.line2,
        landmark=address.landmark,
        city=address.city,
        state=address.state,
        pincode=address.pincode,
        country=address.country,
        is_default_shipping=address.is_default_shipping,
        is_default_billing=address.is_default_billing,
    )


def list_addresses(db: Session, user: User) -> list[Address]:
    return list(
        db.scalars(
            select(Address)
            .where(Address.user_id == user.id)
            .order_by(Address.is_default_shipping.desc(), Address.created_at)
        ).all()
    )


def get_address(db: Session, user: User, address_id: uuid.UUID) -> Address:
    address = db.scalar(select(Address).where(Address.id == address_id, Address.user_id == user.id))
    if address is None:
        raise NotFound("We couldn't find that address.")
    return address


def _clear_defaults(db: Session, user: User, data: AddressIn, keep: uuid.UUID | None) -> None:
    for flag, column in (
        (data.is_default_shipping, Address.is_default_shipping),
        (data.is_default_billing, Address.is_default_billing),
    ):
        if flag:
            stmt = update(Address).where(Address.user_id == user.id, column.is_(True))
            if keep is not None:
                stmt = stmt.where(Address.id != keep)
            db.execute(stmt.values({column.key: False}))


def create_address(db: Session, user: User, data: AddressIn) -> Address:
    count = db.scalar(select(func.count()).select_from(Address).where(Address.user_id == user.id))
    if (count or 0) >= MAX_ADDRESSES:
        raise Conflict(f"You can save up to {MAX_ADDRESSES} addresses.", code="ADDRESS_LIMIT")
    first = count == 0
    _clear_defaults(db, user, data, keep=None)
    address = Address(
        user_id=user.id,
        **data.model_dump(exclude={"is_default_shipping", "is_default_billing"}),
        # The first address becomes the default automatically.
        is_default_shipping=data.is_default_shipping or first,
        is_default_billing=data.is_default_billing or first,
    )
    db.add(address)
    db.flush()
    return address


def update_address(db: Session, user: User, address_id: uuid.UUID, data: AddressIn) -> Address:
    address = get_address(db, user, address_id)
    _clear_defaults(db, user, data, keep=address.id)
    db.flush()
    for key, value in data.model_dump().items():
        setattr(address, key, value)
    db.flush()
    return address


def delete_address(db: Session, user: User, address_id: uuid.UUID) -> None:
    address = get_address(db, user, address_id)
    db.delete(address)
    db.flush()


# --------------------------------------------------------------------------------------------
# Wishlist
# --------------------------------------------------------------------------------------------


def _active_product_ids(db: Session, slugs: list[str]) -> dict[str, uuid.UUID]:
    if not slugs:
        return {}
    rows = db.execute(
        select(Product.slug, Product.id).where(Product.slug.in_(slugs), Product.status == "active")
    ).all()
    return {slug: product_id for slug, product_id in rows}


def wishlist_cards(db: Session, user: User) -> list[ProductCardOut]:
    ids = list(
        db.scalars(
            select(WishlistItem.product_id)
            .join(Product, Product.id == WishlistItem.product_id)
            .where(WishlistItem.user_id == user.id, Product.status == "active")
            .order_by(WishlistItem.created_at.desc())
        ).all()
    )
    return catalogue.cards(db, catalogue._load_products(db, ids))


def add_to_wishlist(db: Session, user: User, slugs: list[str]) -> int:
    """Add products by slug (unknown or inactive slugs are ignored). Returns how many were added."""
    ids = _active_product_ids(db, slugs)
    if not ids:
        return 0
    result = db.execute(
        insert(WishlistItem)
        .values([{"user_id": user.id, "product_id": pid} for pid in ids.values()])
        .on_conflict_do_nothing(index_elements=["user_id", "product_id"])
    )
    return int(getattr(result, "rowcount", 0) or 0)


def remove_from_wishlist(db: Session, user: User, slug: str) -> None:
    product_id = db.scalar(select(Product.id).where(Product.slug == slug))
    if product_id is None:
        return
    item = db.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == user.id, WishlistItem.product_id == product_id
        )
    )
    if item is not None:
        db.delete(item)
        db.flush()


def wishlist_slugs(db: Session, user: User) -> list[str]:
    return list(
        db.scalars(
            select(Product.slug)
            .join(WishlistItem, WishlistItem.product_id == Product.id)
            .where(WishlistItem.user_id == user.id)
            .order_by(WishlistItem.created_at.desc())
        ).all()
    )
