"""Signed-in customer endpoints: profile, address book, wishlist. All scoped to the current user."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.account import AddressIn, AddressOut, ProfileIn, UserOut, WishlistMergeIn
from app.schemas.catalogue import ProductCardOut
from app.schemas.common import OkOut
from app.services import account

router = APIRouter(tags=["account"])


@router.get("/me/profile", response_model=UserOut)
def get_profile(user: User = Depends(get_current_user)) -> UserOut:
    return account.user_out(user)


@router.patch("/me/profile", response_model=UserOut)
def update_profile(
    data: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> UserOut:
    account.update_profile(user, data)
    db.commit()
    return account.user_out(user)


@router.get("/me/addresses", response_model=list[AddressOut])
def list_addresses(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[AddressOut]:
    return [account.address_out(a) for a in account.list_addresses(db, user)]


@router.post("/me/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
def create_address(
    data: AddressIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AddressOut:
    address = account.create_address(db, user, data)
    db.commit()
    return account.address_out(address)


@router.put("/me/addresses/{address_id}", response_model=AddressOut)
def update_address(
    address_id: uuid.UUID,
    data: AddressIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AddressOut:
    address = account.update_address(db, user, address_id, data)
    db.commit()
    return account.address_out(address)


@router.delete("/me/addresses/{address_id}", response_model=OkOut)
def delete_address(
    address_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> OkOut:
    account.delete_address(db, user, address_id)
    db.commit()
    return OkOut(message="Address deleted.")


@router.get("/wishlist", response_model=list[ProductCardOut])
def wishlist(
    response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ProductCardOut]:
    response.headers["Cache-Control"] = "no-store"
    return account.wishlist_cards(db, user)


@router.get("/wishlist/slugs", response_model=list[str])
def wishlist_slugs(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[str]:
    return account.wishlist_slugs(db, user)


@router.put("/wishlist/{slug}", response_model=OkOut)
def add_to_wishlist(
    slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> OkOut:
    account.add_to_wishlist(db, user, [slug])
    db.commit()
    return OkOut(message="Saved to your wishlist.")


@router.delete("/wishlist/{slug}", response_model=OkOut)
def remove_from_wishlist(
    slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> OkOut:
    account.remove_from_wishlist(db, user, slug)
    db.commit()
    return OkOut(message="Removed from your wishlist.")


@router.post("/wishlist/merge", response_model=OkOut)
def merge_wishlist(
    data: WishlistMergeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> OkOut:
    added = account.add_to_wishlist(db, user, data.slugs)
    db.commit()
    return OkOut(message=f"{added} saved pieces added to your account.")
