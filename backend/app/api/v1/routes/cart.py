"""Cart endpoints for guests (cart cookie) and signed-in customers. Every response is the freshly
priced cart; the browser never sends prices."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import Auth, get_app_settings, get_optional_auth
from app.core.config import Settings
from app.core.cookies import set_cookie
from app.core.db import get_db
from app.models import Cart, User
from app.schemas.cart import AddToCartIn, CartOut, CouponIn, UpdateCartItemIn
from app.services import cart as cart_service
from app.services.cart import CART_COOKIE, CART_COOKIE_DAYS

router = APIRouter(prefix="/cart", tags=["cart"])


def _user(auth: Auth | None) -> User | None:
    return auth.user if auth else None


def _respond(
    response: Response,
    db: Session,
    settings: Settings,
    cart: Cart | None,
    user: User | None,
    new_token: str | None = None,
) -> CartOut:
    response.headers["Cache-Control"] = "no-store"
    if new_token:
        set_cookie(
            response,
            settings,
            CART_COOKIE,
            new_token,
            max_age=CART_COOKIE_DAYS * 86_400,
            samesite="lax",
            path="/api",
        )
    return cart_service.cart_view(db, cart, user)


@router.get("", response_model=CartOut)
def get_cart(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    auth: Auth | None = Depends(get_optional_auth),
) -> CartOut:
    user = _user(auth)
    cart = cart_service.find_cart(db, user, request.cookies.get(CART_COOKIE))
    return _respond(response, db, settings, cart, user)


@router.post("/items", response_model=CartOut)
def add_item(
    data: AddToCartIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    auth: Auth | None = Depends(get_optional_auth),
) -> CartOut:
    user = _user(auth)
    cart, new_token = cart_service.get_or_create_cart(db, user, request.cookies.get(CART_COOKIE))
    cart_service.add_item(db, cart, data.variant_id, data.quantity)
    db.commit()
    return _respond(response, db, settings, cart, user, new_token)


@router.patch("/items/{item_id}", response_model=CartOut)
def update_item(
    item_id: uuid.UUID,
    data: UpdateCartItemIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    auth: Auth | None = Depends(get_optional_auth),
) -> CartOut:
    user = _user(auth)
    cart = cart_service.find_cart(db, user, request.cookies.get(CART_COOKIE))
    cart_service.update_item(db, cart, item_id, data.quantity)
    db.commit()
    return _respond(response, db, settings, cart, user)


@router.delete("/items/{item_id}", response_model=CartOut)
def remove_item(
    item_id: uuid.UUID,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    auth: Auth | None = Depends(get_optional_auth),
) -> CartOut:
    user = _user(auth)
    cart = cart_service.find_cart(db, user, request.cookies.get(CART_COOKIE))
    cart_service.remove_item(db, cart, item_id)
    db.commit()
    return _respond(response, db, settings, cart, user)


@router.post("/accept-prices", response_model=CartOut)
def accept_prices(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    auth: Auth | None = Depends(get_optional_auth),
) -> CartOut:
    user = _user(auth)
    cart = cart_service.find_cart(db, user, request.cookies.get(CART_COOKIE))
    cart_service.accept_prices(db, cart, user)
    db.commit()
    return _respond(response, db, settings, cart, user)


@router.post("/coupon", response_model=CartOut)
def apply_coupon(
    data: CouponIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    auth: Auth | None = Depends(get_optional_auth),
) -> CartOut:
    user = _user(auth)
    cart, new_token = cart_service.get_or_create_cart(db, user, request.cookies.get(CART_COOKIE))
    cart_service.apply_coupon(db, cart, user, data.code)
    db.commit()
    return _respond(response, db, settings, cart, user, new_token)


@router.delete("/coupon", response_model=CartOut)
def remove_coupon(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    auth: Auth | None = Depends(get_optional_auth),
) -> CartOut:
    user = _user(auth)
    cart = cart_service.find_cart(db, user, request.cookies.get(CART_COOKIE))
    cart_service.remove_coupon(db, cart)
    db.commit()
    return _respond(response, db, settings, cart, user)
