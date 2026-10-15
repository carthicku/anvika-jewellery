"""Checkout: shipping quote and order creation (docs/architecture/INVENTORY_AND_ORDERS.md §3).

Order creation happens in ONE database transaction: lock the cart, re-price everything on the
server, compare with the total the customer agreed to, reserve stock under row locks, lock the
coupon for its usage limits, and write the order with immutable line snapshots. The payment
provider is called only after that transaction commits (see payments.start_payment).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, Conflict, PriceChanged, ValidationFailed
from app.core.money import format_inr
from app.core.security import hash_token
from app.core.time import utcnow
from app.models import Cart, Coupon, CouponRedemption, Order, OrderItem, User
from app.schemas.account import AddressFieldsIn
from app.schemas.orders import CheckoutQuoteIn, CheckoutQuoteOut, CreateOrderIn
from app.services import cart as cart_service
from app.services import inventory, orders, shipping
from app.services.cart import CouponInvalid, PricedCart
from app.services.pricing import ShippingInput
from app.services.shipping import ShippingOptionOut

IDEMPOTENCY_KEY_PATTERN = r"^[A-Za-z0-9_-]{16,64}$"


class CartNotReady(AppError):
    status_code = 409
    code = "CART_NOT_READY"
    message = "Your cart needs attention before checkout."


@dataclass
class CheckoutResult:
    order: Order
    created: bool  # False when an existing order was returned (idempotent replay / reuse)


# --------------------------------------------------------------------------------------------
# Quote (no side effects)
# --------------------------------------------------------------------------------------------


def _shipping_input(option: ShippingOptionOut) -> ShippingInput:
    return ShippingInput(option.code, option.name, option.fee, option.free_above)


def quote(
    db: Session, user: User | None, cart: Cart | None, data: CheckoutQuoteIn
) -> CheckoutQuoteOut:
    pincode = shipping.validate_pincode(data.pincode)
    options = shipping.options_for(db, pincode) or []
    selected = next((o for o in options if o.code == data.shipping_method), None)
    if selected is None and options:
        selected = options[0]
    view = cart_service.cart_view(
        db, cart, user, shipping_input=_shipping_input(selected) if selected else None
    )
    message = None
    if not options:
        message = "Sorry, we don't deliver to this PIN code yet."
        view.can_checkout = False
        view.blocking_issues.append(message)
    return CheckoutQuoteOut(
        cart=view,
        pincode=pincode,
        serviceable=bool(options),
        message=message,
        shipping_options=options,
        shipping_method=selected.code if selected else None,
    )


# --------------------------------------------------------------------------------------------
# Order creation
# --------------------------------------------------------------------------------------------


def _fingerprint(cart: Cart, priced: PricedCart, data: CreateOrderIn, email: str) -> str:
    """What the customer is buying and where it goes. Same fingerprint + same total → the
    existing pending order is reused instead of creating a duplicate."""
    payload = {
        "lines": sorted((str(ln.variant.id), ln.item.quantity) for ln in priced.lines),
        "coupon": cart.coupon_code,
        "shipping_method": data.shipping_method,
        "shipping": data.shipping_address.model_dump(),
        "billing": data.billing_address.model_dump() if data.billing_address else None,
        "email": email,
        "note": data.customer_note,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _lock_cart(db: Session, cart: Cart) -> Cart:
    locked = db.scalar(
        select(Cart)
        .where(Cart.id == cart.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked is None or locked.status != "active":
        raise CartNotReady("Your cart has changed. Please review it and try again.")
    return locked


def _supersede_pending(db: Session, order: Order) -> None:
    """A newer checkout from the same cart replaces an unpaid pending order."""
    locked = orders.lock_order(db, order.id)
    if locked.status != "pending_payment":
        return
    if locked.payment_status == "authorized":
        raise Conflict(
            "A payment for your previous checkout attempt is still being confirmed. Please wait a "
            "few minutes and check your orders before trying again.",
            code="PAYMENT_IN_PROGRESS",
        )
    inventory.release(db, locked.id, note="Replaced by a newer checkout")
    orders.set_redemption_status(db, locked, "released")
    locked.pricing_context = {**locked.pricing_context, "superseded": True}
    orders.transition(
        db,
        locked,
        "expired",
        kind="order_expired",
        actor_type="system",
        note="Replaced by a newer checkout attempt",
        customer_visible=False,
    )


def _check_coupon_limits(db: Session, coupon: Coupon, user: User | None, email: str) -> None:
    """Re-check usage limits while holding the coupon row lock (two checkouts can't both take
    the last use). Guests are limited per email address."""
    db.execute(select(Coupon.id).where(Coupon.id == coupon.id).with_for_update())
    counted = CouponRedemption.status.in_(("reserved", "redeemed"))
    total = db.scalar(
        select(func.count())
        .select_from(CouponRedemption)
        .where(CouponRedemption.coupon_id == coupon.id, counted)
    )
    if coupon.usage_limit_total is not None and (total or 0) >= coupon.usage_limit_total:
        raise CouponInvalid("This coupon has reached its usage limit.", code="COUPON_USAGE_LIMIT")
    if coupon.usage_limit_per_customer is not None:
        owner = (
            CouponRedemption.user_id == user.id
            if user is not None
            else func.lower(CouponRedemption.email) == email.lower()
        )
        mine = db.scalar(
            select(func.count())
            .select_from(CouponRedemption)
            .where(CouponRedemption.coupon_id == coupon.id, counted, owner)
        )
        if (mine or 0) >= coupon.usage_limit_per_customer:
            raise CouponInvalid("You have already used this coupon.", code="COUPON_USAGE_LIMIT")


def _json_safe(value: Any) -> Any:
    """JSONB snapshots store money as exact strings (never floats)."""
    return json.loads(json.dumps(value, default=str))


def _address_snapshot(address: AddressFieldsIn) -> dict[str, Any]:
    return {**address.model_dump(), "country": "IN"}


def find_by_idempotency_key(db: Session, key: str) -> Order | None:
    return db.scalar(select(Order).where(Order.idempotency_key == key))


def create_order(
    db: Session,
    settings: Settings,
    user: User | None,
    cart: Cart | None,
    data: CreateOrderIn,
    idempotency_key: str,
) -> CheckoutResult:
    # 0. Same request repeated (double click, network retry) → the same order.
    existing = find_by_idempotency_key(db, idempotency_key)
    if existing is not None:
        if cart is None or existing.cart_id != cart.id:
            raise Conflict(
                "This checkout request was already used. Please refresh and try again.",
                code="IDEMPOTENCY_KEY_REUSED",
            )
        return CheckoutResult(existing, created=False)

    if not data.terms_accepted:
        raise ValidationFailed({"terms_accepted": "Please accept the terms to place your order."})
    if user is not None:
        email = user.email
    elif data.email:
        email = str(data.email).lower()
    else:
        raise ValidationFailed({"email": "Enter your email address so we can send your receipt."})
    if cart is None:
        raise CartNotReady("Your cart is empty.", code="CART_EMPTY")

    # 1. Serialise checkouts of this cart.
    cart = _lock_cart(db, cart)

    # 2. Delivery.
    pincode = data.shipping_address.pincode
    options = shipping.options_for(db, pincode)
    if not options:
        raise ValidationFailed(
            {"shipping_address.pincode": "Sorry, we don't deliver to this PIN code yet."}
        )
    option = next((o for o in options if o.code == data.shipping_method), None)
    if option is None:
        raise ValidationFailed(
            {"shipping_method": "Choose one of the delivery options for this PIN code."}
        )

    # 3. Fresh server-side prices, exactly as the cart/quote shows them.
    priced = cart_service.price_cart(db, cart, user, shipping_input=_shipping_input(option))
    view = cart_service.cart_view(db, cart, user, priced=priced)
    if not priced.lines:
        raise CartNotReady("Your cart is empty.", code="CART_EMPTY")
    if not view.can_checkout or priced.order is None:
        raise CartNotReady(details={"blocking_issues": view.blocking_issues})
    price = priced.order

    # 4. Reuse or replace a pending order made from this cart.
    fingerprint = _fingerprint(cart, priced, data, email)
    now = utcnow()
    pending = db.scalars(
        select(Order).where(Order.cart_id == cart.id, Order.status == "pending_payment")
    ).all()
    for order in pending:
        if (
            order.pricing_context.get("fingerprint") == fingerprint
            and order.grand_total == data.expected_total
            and order.payment_expires_at > now
            and order.payment_status in ("unpaid", "failed")
        ):
            return CheckoutResult(order, created=False)
        _supersede_pending(db, order)

    # 5. The customer must have agreed to exactly this total.
    if price.grand_total != data.expected_total:
        raise PriceChanged(
            f"The total has changed to {format_inr(price.grand_total)}. "
            "Please review the updated total before paying.",
            details={"grand_total": str(price.grand_total)},
        )

    # 6. Coupon usage limits under lock.
    coupon = priced.coupon if price.coupon_discount > 0 else None
    if coupon is not None:
        _check_coupon_limits(db, coupon, user, email)

    # 7. Write the order and its snapshots.
    expires_at = now + timedelta(minutes=settings.payment_window_minutes)
    billing = data.billing_address or data.shipping_address
    order = Order(
        reference=orders.new_reference(db, settings),
        user_id=user.id if user else None,
        cart_id=cart.id,
        email=email,
        phone=data.shipping_address.phone,
        customer_name=data.shipping_address.full_name,
        status="pending_payment",
        payment_status="unpaid",
        currency="INR",
        subtotal=price.subtotal,
        automatic_discount=price.automatic_discount,
        coupon_discount=price.coupon_discount,
        taxable_total=price.taxable_total,
        tax_total=price.tax_total,
        shipping_total=price.shipping_fee + price.shipping_tax,
        rounding_adjustment=price.rounding_adjustment,
        grand_total=price.grand_total,
        coupon_code=coupon.code if coupon else None,
        shipping_address=_address_snapshot(data.shipping_address),
        billing_address=_address_snapshot(billing),
        shipping_method={
            "code": option.code,
            "name": option.name,
            "fee": str(option.fee),
            "free_above": str(option.free_above) if option.free_above is not None else None,
            "min_days": option.min_days,
            "max_days": option.max_days,
            "estimated_from": option.estimated_from.isoformat(),
            "estimated_to": option.estimated_to.isoformat(),
        },
        pricing_context={
            "engine_version": price.engine_version,
            "tax_rates": price.tax_rates.as_dict(),
            "shipping_fee": str(price.shipping_fee),
            "shipping_tax": str(price.shipping_tax),
            "breakdown": _json_safe(price.breakdown),
            "fingerprint": fingerprint,
        },
        customer_note=data.customer_note,
        idempotency_key=idempotency_key,
        terms_accepted_at=now,
        payment_expires_at=expires_at,
    )
    db.add(order)
    db.flush()
    if user is None:
        order.guest_access_token_hash = hash_token(orders.guest_access_token(settings, order.id))

    line_prices = {lp.key: lp for lp in price.lines}
    for position, line in enumerate(priced.lines):
        lp = line_prices[str(line.item.id)]
        unit = line.unit
        if unit is None:  # guarded by can_checkout above
            raise CartNotReady()
        images = line.product.images
        db.add(
            OrderItem(
                order_id=order.id,
                position=position,
                product_id=line.product.id,
                variant_id=line.variant.id,
                product_name=line.product.name,
                product_slug=line.product.slug,
                variant_label=line.variant.label,
                sku=line.variant.sku,
                purity=line.product.purity,
                image_url=images[0].url if images else None,
                quantity=line.item.quantity,
                unit_price=unit.total,
                line_components={k: str(v) for k, v in lp.components.items()},
                line_discount=lp.discount,
                line_taxable_value=lp.taxable_value,
                line_tax=lp.tax,
                line_total=lp.total,
                price_inputs=_json_safe(
                    {
                        **unit.inputs,
                        "automatic_discount": {k: str(v) for k, v in lp.automatic_discount.items()},
                        "coupon_discount": {k: str(v) for k, v in lp.coupon_discount.items()},
                        "tax_by_component": {k: str(v) for k, v in lp.tax_by_component.items()},
                        "return_eligible": line.product.return_eligible,
                        "exchange_eligible": line.product.exchange_eligible,
                    }
                ),
            )
        )

    # 8. Hold the stock (raises OUT_OF_STOCK and rolls everything back if someone was faster).
    inventory.reserve(
        db, order.id, [(ln.variant.id, ln.item.quantity) for ln in priced.lines], expires_at
    )
    if coupon is not None:
        db.add(
            CouponRedemption(
                coupon_id=coupon.id,
                order_id=order.id,
                user_id=user.id if user else None,
                email=email,
                amount=price.coupon_discount,
                status="reserved",
            )
        )
    orders.add_event(
        db,
        order,
        "order_created",
        actor_type="customer",
        actor_user_id=user.id if user else None,
        to_status="pending_payment",
    )
    db.flush()
    return CheckoutResult(order, created=True)
