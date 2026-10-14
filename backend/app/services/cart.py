"""Shopping cart: guest (hashed cookie token) or customer cart, priced by the backend on every read.

Rules (docs/architecture/PRICING_ENGINE.md §6, INVENTORY_AND_ORDERS.md §1):
* Prices are recalculated on every read; the browser never supplies a price.
* A price INCREASE since the customer last accepted it blocks checkout until accepted again.
  A decrease is shown as good news and never blocks.
* The cart checks stock but does not reserve it (reservation happens when an order is created).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, Conflict, NotFound, OutOfStock
from app.core.money import ZERO, format_inr
from app.core.security import hash_token, new_token
from app.core.time import utcnow
from app.models import (
    Cart,
    CartItem,
    Coupon,
    CouponRedemption,
    Product,
    ProductVariant,
    User,
)
from app.models.cart import MAX_LINE_QUANTITY
from app.schemas.cart import (
    CartLineOut,
    CartOut,
    CartTotalsOut,
    CouponStateOut,
)
from app.schemas.catalogue import PriceRowOut
from app.services import inventory, shipping
from app.services.catalogue import image_out
from app.services.pricing import (
    CouponInput,
    OrderLine,
    OrderPrice,
    PriceUnavailable,
    ShippingInput,
    UnitPrice,
    price_order,
)
from app.services.pricing_context import PricingContext, load_pricing_context

CART_COOKIE = "cart_token"
CART_COOKIE_DAYS = 60

COUPON_MESSAGES = {
    "MIN_ORDER_NOT_MET": "Your order needs to reach {min} before this coupon applies.",
    "NOTHING_TO_DISCOUNT": "Add items to your cart to use this coupon.",
}


class CouponInvalid(AppError):
    status_code = 422
    code = "COUPON_INVALID"
    message = "This coupon can't be used."


# --------------------------------------------------------------------------------------------
# Finding and creating carts
# --------------------------------------------------------------------------------------------


def find_cart(db: Session, user: User | None, token: str | None) -> Cart | None:
    """The active cart for this customer, or for this browser's guest token."""
    if user is not None:
        return db.scalar(select(Cart).where(Cart.user_id == user.id, Cart.status == "active"))
    if token:
        return db.scalar(
            select(Cart).where(
                Cart.token_hash == hash_token(token),
                Cart.user_id.is_(None),
                Cart.status == "active",
            )
        )
    return None


def get_or_create_cart(
    db: Session, user: User | None, token: str | None
) -> tuple[Cart, str | None]:
    """Return (cart, new_guest_token). A new token is returned only when a guest cart is created
    and must be set as the cart cookie."""
    cart = find_cart(db, user, token)
    if cart is not None:
        return cart, None
    if user is not None:
        cart = Cart(id=uuid.uuid4(), user_id=user.id, status="active")
        db.add(cart)
        db.flush()
        return cart, None
    fresh = new_token()
    cart = Cart(id=uuid.uuid4(), token_hash=hash_token(fresh), status="active")
    db.add(cart)
    db.flush()
    return cart, fresh


# --------------------------------------------------------------------------------------------
# Coupons
# --------------------------------------------------------------------------------------------


def _coupon_usage(db: Session, coupon: Coupon, user: User | None) -> tuple[int, int]:
    counted = CouponRedemption.status.in_(("reserved", "redeemed"))
    total = (
        db.scalar(
            select(func.count())
            .select_from(CouponRedemption)
            .where(CouponRedemption.coupon_id == coupon.id, counted)
        )
        or 0
    )
    mine = 0
    if user is not None:
        mine = (
            db.scalar(
                select(func.count())
                .select_from(CouponRedemption)
                .where(
                    CouponRedemption.coupon_id == coupon.id,
                    CouponRedemption.user_id == user.id,
                    counted,
                )
            )
            or 0
        )
    return total, mine


def check_coupon(db: Session, code: str, user: User | None) -> Coupon:
    """Validate everything about a coupon except the order amount (the engine checks that)."""
    coupon = db.scalar(select(Coupon).where(Coupon.code == code.strip().upper()))
    now = utcnow()
    if coupon is None or not coupon.is_active:
        raise CouponInvalid("We don't recognise that coupon code.", code="COUPON_NOT_FOUND")
    if coupon.starts_at > now:
        raise CouponInvalid("This coupon isn't active yet.", code="COUPON_NOT_STARTED")
    if coupon.ends_at is not None and coupon.ends_at <= now:
        raise CouponInvalid("This coupon has expired.", code="COUPON_EXPIRED")
    total, mine = _coupon_usage(db, coupon, user)
    if coupon.usage_limit_total is not None and total >= coupon.usage_limit_total:
        raise CouponInvalid("This coupon has reached its usage limit.", code="COUPON_USAGE_LIMIT")
    if coupon.usage_limit_per_customer is not None and mine >= coupon.usage_limit_per_customer:
        raise CouponInvalid("You have already used this coupon.", code="COUPON_USAGE_LIMIT")
    return coupon


def coupon_input(coupon: Coupon) -> CouponInput:
    return CouponInput(
        code=coupon.code,
        kind=coupon.kind,
        value=coupon.value,
        max_discount_amount=coupon.max_discount_amount,
        min_order_amount=coupon.min_order_amount,
    )


# --------------------------------------------------------------------------------------------
# Pricing a cart
# --------------------------------------------------------------------------------------------


@dataclass
class PricedLine:
    item: CartItem
    variant: ProductVariant
    product: Product
    unit: UnitPrice | None
    available: int
    issue: str | None
    price_change: str | None


@dataclass
class PricedCart:
    lines: list[PricedLine]
    order: OrderPrice | None
    coupon: Coupon | None
    coupon_message: str | None
    shipping: ShippingInput | None


def _load_lines(db: Session, cart: Cart) -> list[tuple[CartItem, ProductVariant, Product]]:
    items = list(
        db.scalars(
            select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.created_at)
        ).all()
    )
    if not items:
        return []
    variants = {
        v.id: v
        for v in db.scalars(
            select(ProductVariant)
            .where(ProductVariant.id.in_([i.variant_id for i in items]))
            .options(
                selectinload(ProductVariant.product).selectinload(Product.images),
                selectinload(ProductVariant.product).selectinload(Product.category),
            )
        ).all()
    }
    return [(i, variants[i.variant_id], variants[i.variant_id].product) for i in items]


def default_shipping(db: Session) -> ShippingInput | None:
    methods = shipping.active_methods(db)
    if not methods:
        return None
    first = methods[0]
    return ShippingInput(first.code, first.name, first.fee, first.free_above)


def price_cart(
    db: Session,
    cart: Cart,
    user: User | None,
    *,
    shipping_input: ShippingInput | None = None,
    ctx: PricingContext | None = None,
) -> PricedCart:
    rows = _load_lines(db, cart)
    ctx = ctx or load_pricing_context(db, [p for _, _, p in rows])
    levels = inventory.levels_for(db, [v.id for _, v, _ in rows])
    lines: list[PricedLine] = []
    for item, variant, product in rows:
        level = levels.get(variant.id)
        available = level.available if level else 0
        unit: UnitPrice | None = None
        issue: str | None = None
        if product.status != "active" or not variant.is_active:
            issue = "unavailable"
        else:
            try:
                unit = ctx.price(product, variant)
            except PriceUnavailable:
                issue = "price_unavailable"
        if issue is None:
            if available <= 0:
                issue = "out_of_stock"
            elif item.quantity > available:
                issue = "insufficient_stock"
        change = None
        if unit is not None:
            if unit.total > item.accepted_unit_price:
                change = "increased"
            elif unit.total < item.accepted_unit_price:
                change = "decreased"
        lines.append(PricedLine(item, variant, product, unit, available, issue, change))

    coupon: Coupon | None = None
    coupon_message: str | None = None
    if cart.coupon_code:
        try:
            coupon = check_coupon(db, cart.coupon_code, user)
        except CouponInvalid as exc:
            coupon_message = exc.message

    priceable = [ln for ln in lines if ln.unit is not None and ln.issue is None]
    order = None
    ship = shipping_input if shipping_input is not None else default_shipping(db)
    if priceable:
        order = price_order(
            [
                OrderLine(unit=ln.unit, quantity=ln.item.quantity, key=str(ln.item.id))
                for ln in priceable
                if ln.unit is not None
            ],
            ctx.tax,
            coupon=coupon_input(coupon) if coupon else None,
            shipping=ship,
        )
        if coupon is not None and order.coupon_error:
            template = COUPON_MESSAGES.get(order.coupon_error, "This coupon can't be used.")
            coupon_message = template.format(min=format_inr(coupon.min_order_amount or ZERO))
    return PricedCart(lines, order, coupon, coupon_message, ship)


def _line_message(line: PricedLine) -> str | None:
    name = line.product.name
    if line.issue == "unavailable":
        return f"{name} is no longer available. Please remove it from your cart."
    if line.issue == "price_unavailable":
        return f"{name} can't be priced right now. Please remove it or contact us."
    if line.issue == "out_of_stock":
        return f"{name} is out of stock. Please remove it from your cart."
    if line.issue == "insufficient_stock":
        return f"Only {line.available} of {name} available. Please reduce the quantity."
    return None


def cart_view(db: Session, cart: Cart | None, user: User | None) -> CartOut:
    if cart is None:
        return CartOut(
            lines=[],
            item_count=0,
            totals=None,
            coupon=None,
            can_checkout=False,
            blocking_issues=[],
            notices=[],
        )
    priced = price_cart(db, cart, user)
    blocking: list[str] = []
    notices: list[str] = []
    out_lines: list[CartLineOut] = []
    order_lines = {lp.key: lp for lp in priced.order.lines} if priced.order else {}

    for line in priced.lines:
        message = _line_message(line)
        if message:
            blocking.append(message)
        if line.unit is not None and line.price_change == "increased":
            blocking.append(
                f"The price of {line.product.name} has gone up from "
                f"{format_inr(line.item.accepted_unit_price)} to {format_inr(line.unit.total)}. "
                "Please review and accept the updated prices."
            )
        elif line.unit is not None and line.price_change == "decreased":
            notices.append(
                f"Good news — {line.product.name} is now {format_inr(line.unit.total)} "
                f"(was {format_inr(line.item.accepted_unit_price)})."
            )
        priced_line = order_lines.get(str(line.item.id))
        images = line.product.images
        out_lines.append(
            CartLineOut(
                id=str(line.item.id),
                product_slug=line.product.slug,
                product_name=line.product.name,
                variant_id=str(line.variant.id),
                variant_label=line.variant.label,
                size=line.variant.size,
                sku=line.variant.sku,
                purity=line.product.purity,
                image=image_out(images[0]) if images else None,
                quantity=line.item.quantity,
                max_quantity=max(1, min(MAX_LINE_QUANTITY, line.available)),
                stock_status=inventory.stock_status_for(line.available),
                unit_price=line.unit.total if line.unit else None,
                accepted_unit_price=line.item.accepted_unit_price,
                price_change=line.price_change,
                # Before the order-level coupon (shown once in the summary), so line totals
                # always equal "price each × quantity" for the customer.
                line_total=line.unit.total * line.item.quantity
                if priced_line and line.unit
                else None,
                issue=line.issue,
            )
        )

    order = priced.order
    totals = None
    if order is not None:
        totals = CartTotalsOut(
            subtotal=order.subtotal,
            automatic_discount=order.automatic_discount,
            coupon_discount=order.coupon_discount,
            tax_total=order.tax_total,
            shipping_fee=order.shipping_fee,
            shipping_label=priced.shipping.name if priced.shipping else None,
            free_shipping_above=priced.shipping.free_above if priced.shipping else None,
            rounding_adjustment=order.rounding_adjustment,
            grand_total=order.grand_total,
            breakdown=[PriceRowOut(**row) for row in order.breakdown],
        )

    coupon_state = None
    if cart.coupon_code:
        applied = bool(order and order.coupon_discount > 0 and priced.coupon_message is None)
        coupon_state = CouponStateOut(
            code=cart.coupon_code,
            applied=applied,
            message=priced.coupon_message
            or (f"You save {format_inr(order.coupon_discount)}." if applied and order else None),
        )
    return CartOut(
        lines=out_lines,
        item_count=sum(ln.item.quantity for ln in priced.lines),
        totals=totals,
        coupon=coupon_state,
        can_checkout=bool(out_lines) and not blocking,
        blocking_issues=blocking,
        notices=notices,
    )


# --------------------------------------------------------------------------------------------
# Mutations
# --------------------------------------------------------------------------------------------


def _current_unit_price(db: Session, variant: ProductVariant) -> Decimal:
    product = variant.product
    if product.status != "active" or not variant.is_active:
        raise NotFound("This piece is no longer available.")
    ctx = load_pricing_context(db, [product])
    try:
        return ctx.price(product, variant).total
    except PriceUnavailable as exc:
        raise Conflict(
            "This piece can't be priced right now, so it can't be added to your cart.",
            code="PRICE_UNAVAILABLE",
        ) from exc


def _ensure_stock(db: Session, variant: ProductVariant, quantity: int) -> None:
    level = inventory.levels_for(db, [variant.id]).get(variant.id)
    available = level.available if level else 0
    if available < quantity:
        raise OutOfStock(
            "Sorry, that's more than we have in stock."
            if available > 0
            else "Sorry, this piece is out of stock.",
            details={"available": max(0, available)},
        )


def _get_variant(db: Session, variant_id: uuid.UUID) -> ProductVariant:
    variant = db.scalar(
        select(ProductVariant)
        .where(ProductVariant.id == variant_id)
        .options(selectinload(ProductVariant.product))
    )
    if variant is None:
        raise NotFound("This piece is no longer available.")
    return variant


def add_item(db: Session, cart: Cart, variant_id: uuid.UUID, quantity: int) -> None:
    variant = _get_variant(db, variant_id)
    price = _current_unit_price(db, variant)
    item = db.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant.id)
    )
    new_quantity = quantity + (item.quantity if item else 0)
    if new_quantity > MAX_LINE_QUANTITY:
        raise Conflict(
            f"You can buy up to {MAX_LINE_QUANTITY} of a piece in one order.",
            code="QUANTITY_LIMIT",
        )
    _ensure_stock(db, variant, new_quantity)
    if item is None:
        db.add(
            CartItem(
                cart_id=cart.id,
                variant_id=variant.id,
                quantity=new_quantity,
                accepted_unit_price=price,
            )
        )
    else:
        item.quantity = new_quantity
        item.accepted_unit_price = price  # the customer is looking at the current price now
    cart.updated_at = utcnow()
    db.flush()


def _get_item(db: Session, cart: Cart | None, item_id: uuid.UUID) -> CartItem:
    if cart is None:
        raise NotFound("That item isn't in your cart.")
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    if item is None:
        raise NotFound("That item isn't in your cart.")
    return item


def update_item(db: Session, cart: Cart | None, item_id: uuid.UUID, quantity: int) -> None:
    item = _get_item(db, cart, item_id)
    if quantity > item.quantity:
        _ensure_stock(db, _get_variant(db, item.variant_id), quantity)
    item.quantity = quantity
    db.flush()


def remove_item(db: Session, cart: Cart | None, item_id: uuid.UUID) -> None:
    item = _get_item(db, cart, item_id)
    db.delete(item)
    db.flush()


def accept_prices(db: Session, cart: Cart | None, user: User | None) -> None:
    """Record that the customer has seen and accepted every current price."""
    if cart is None:
        return
    for line in price_cart(db, cart, user).lines:
        if line.unit is not None:
            line.item.accepted_unit_price = line.unit.total
    db.flush()


def apply_coupon(db: Session, cart: Cart, user: User | None, code: str) -> None:
    coupon = check_coupon(db, code, user)
    cart.coupon_code = coupon.code
    db.flush()


def remove_coupon(db: Session, cart: Cart | None) -> None:
    if cart is not None:
        cart.coupon_code = None
        db.flush()


def merge_guest_cart(db: Session, token: str | None, user: User) -> None:
    """At sign-in, move the guest cart's lines into the customer's cart (quantities combined,
    capped at the per-line limit; stock is re-checked when the cart is viewed)."""
    guest = find_cart(db, None, token)
    if guest is None:
        return
    target, _ = get_or_create_cart(db, user, None)
    existing = {
        i.variant_id: i
        for i in db.scalars(select(CartItem).where(CartItem.cart_id == target.id)).all()
    }
    for item in db.scalars(select(CartItem).where(CartItem.cart_id == guest.id)).all():
        if item.variant_id in existing:
            mine = existing[item.variant_id]
            mine.quantity = min(MAX_LINE_QUANTITY, mine.quantity + item.quantity)
            mine.accepted_unit_price = max(mine.accepted_unit_price, item.accepted_unit_price)
            db.delete(item)
        else:
            item.cart_id = target.id
    if target.coupon_code is None and guest.coupon_code:
        target.coupon_code = guest.coupon_code
    guest.status = "merged"
    db.flush()
