"""Checkout: delivery quote and order creation. Prices always come from the backend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Auth, get_app_settings, get_gateway, get_optional_auth
from app.core.config import Settings
from app.core.db import get_db
from app.core.errors import PaymentProviderError
from app.core.rate_limit import rate_limit
from app.schemas.orders import CheckoutOrderOut, CheckoutQuoteIn, CheckoutQuoteOut, CreateOrderIn
from app.services import cart as cart_service
from app.services import checkout, orders, payments
from app.services.cart import CART_COOKIE
from app.services.checkout import IDEMPOTENCY_KEY_PATTERN, CheckoutResult
from app.services.payment_gateway import PaymentGateway

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post(
    "/quote",
    response_model=CheckoutQuoteOut,
    dependencies=[Depends(rate_limit("checkout-quote-ip", limit=120, window_seconds=600))],
)
def quote(
    data: CheckoutQuoteIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    auth: Auth | None = Depends(get_optional_auth),
) -> CheckoutQuoteOut:
    """Delivery options and the full price breakdown for a PIN code. Changes nothing."""
    response.headers["Cache-Control"] = "no-store"
    user = auth.user if auth else None
    cart = cart_service.find_cart(db, user, request.cookies.get(CART_COOKIE))
    return checkout.quote(db, user, cart, data)


@router.post(
    "/orders",
    response_model=CheckoutOrderOut,
    dependencies=[Depends(rate_limit("checkout-order-ip", limit=30, window_seconds=600))],
)
def create_order(
    data: CreateOrderIn,
    request: Request,
    response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key", pattern=IDEMPOTENCY_KEY_PATTERN),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    gateway: PaymentGateway = Depends(get_gateway),
    auth: Auth | None = Depends(get_optional_auth),
) -> CheckoutOrderOut:
    """Re-price the cart, check `expected_total`, reserve stock and create a pending order, then
    open a payment with the provider. Repeating the same Idempotency-Key returns the same order."""
    response.headers["Cache-Control"] = "no-store"
    user = auth.user if auth else None
    cart = cart_service.find_cart(db, user, request.cookies.get(CART_COOKIE))
    try:
        result = checkout.create_order(db, settings, user, cart, data, idempotency_key)
        db.commit()
    except IntegrityError:
        # Two identical requests raced; the other one created the order.
        db.rollback()
        existing = checkout.find_by_idempotency_key(db, idempotency_key)
        if existing is None or cart is None or existing.cart_id != cart.id:
            raise
        result = CheckoutResult(existing, created=False)

    order = result.order
    payment_session = None
    payment_error = None
    if orders.can_pay(order):
        attempt = None if result.created else payments.latest_open_attempt(db, order)
        if attempt is None:
            try:
                attempt = payments.start_payment(db, gateway, order)
                db.commit()
            except PaymentProviderError as exc:
                db.rollback()
                payment_error = exc.message
        if attempt is not None:
            payment_session = payments.payment_session(settings, gateway, order, attempt)
    return CheckoutOrderOut(
        order=orders.order_view(db, order),
        access_token=orders.guest_access_token(settings, order.id)
        if order.user_id is None
        else None,
        payment=payment_session,
        payment_error=payment_error,
    )
