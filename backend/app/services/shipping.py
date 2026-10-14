"""Shipping methods and PIN-code serviceability (docs/operations/SHIPPING_SETUP.md).

PIN codes are validated by format and against admin-configured zones only — there is no
city/state lookup because no verified dataset has been chosen (ASSUMPTIONS C4).
"""

from __future__ import annotations

import re
from datetime import date, timedelta, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.core.money import MoneyStr
from app.core.time import utcnow
from app.models import ShippingMethod, ShippingZone

PINCODE_RE = re.compile(r"^[1-9][0-9]{5}$")
IST = timezone(timedelta(hours=5, minutes=30))


class ShippingOptionOut(BaseModel):
    code: str
    name: str
    description: str | None
    fee: MoneyStr
    free_above: MoneyStr | None
    min_days: int
    max_days: int
    estimated_from: date
    estimated_to: date


class PincodeCheckOut(BaseModel):
    pincode: str
    serviceable: bool
    message: str
    options: list[ShippingOptionOut]


def validate_pincode(pincode: str) -> str:
    value = pincode.strip()
    if not PINCODE_RE.match(value):
        raise ValidationFailed({"pincode": "Enter a valid 6-digit Indian PIN code."})
    return value


def zone_extra_days(db: Session, pincode: str) -> int | None:
    """None = not serviceable. 0+ = serviceable with that many extra days."""
    zones = db.scalars(select(ShippingZone).where(ShippingZone.is_active.is_(True))).all()
    if not zones:
        return 0
    matches = [
        z.extra_days for z in zones if any(pincode.startswith(p) for p in z.pincode_prefixes)
    ]
    return min(matches) if matches else None


def active_methods(db: Session) -> list[ShippingMethod]:
    return list(
        db.scalars(
            select(ShippingMethod)
            .where(ShippingMethod.is_active.is_(True))
            .order_by(ShippingMethod.sort_order, ShippingMethod.fee)
        ).all()
    )


def options_for(db: Session, pincode: str) -> list[ShippingOptionOut] | None:
    extra = zone_extra_days(db, pincode)
    if extra is None:
        return None
    today = utcnow().astimezone(IST).date()
    return [
        ShippingOptionOut(
            code=m.code,
            name=m.name,
            description=m.description,
            fee=m.fee,
            free_above=m.free_above,
            min_days=m.min_days + extra,
            max_days=m.max_days + extra,
            estimated_from=today + timedelta(days=m.min_days + extra),
            estimated_to=today + timedelta(days=m.max_days + extra),
        )
        for m in active_methods(db)
    ]


def check_pincode(db: Session, pincode: str) -> PincodeCheckOut:
    pin = validate_pincode(pincode)
    options = options_for(db, pin)
    if not options:
        return PincodeCheckOut(
            pincode=pin,
            serviceable=False,
            message="Sorry, we don't deliver to this PIN code yet.",
            options=[],
        )
    fastest = min(options, key=lambda o: o.min_days)
    return PincodeCheckOut(
        pincode=pin,
        serviceable=True,
        message=f"Delivery in {fastest.min_days}–{fastest.max_days} days.",
        options=options,
    )


def get_method(db: Session, code: str) -> ShippingMethod | None:
    return db.scalar(
        select(ShippingMethod).where(ShippingMethod.code == code, ShippingMethod.is_active)
    )
