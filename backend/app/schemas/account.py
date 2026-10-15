"""Request/response models for authentication and the customer account."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import StrictIn

INDIAN_STATES = (
    "Andaman and Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
)  # 28 states + 8 union territories

_MOBILE_RE = re.compile(r"^(?:\+?91)?([6-9]\d{9})$")


def normalise_indian_mobile(value: str) -> str:
    """Accept 98765 43210 / +91-9876543210 / 919876543210 → "+919876543210"."""
    digits = re.sub(r"[\s\-()]", "", value)
    match = _MOBILE_RE.match(digits)
    if not match:
        raise ValueError("Enter a valid 10-digit Indian mobile number.")
    return f"+91{match.group(1)}"


class RegisterIn(StrictIn):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalise_indian_mobile(value) if value else None


class LoginIn(StrictIn):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenIn(StrictIn):
    token: str = Field(min_length=16, max_length=128)


class ForgotPasswordIn(StrictIn):
    email: EmailStr


class ResetPasswordIn(StrictIn):
    token: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(StrictIn):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None
    role: Literal["customer", "staff", "admin"]
    email_verified: bool
    permissions: list[str]


class MeOut(BaseModel):
    user: UserOut | None


class SessionOut(BaseModel):
    id: str
    device: str
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime
    current: bool


class ProfileIn(StrictIn):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalise_indian_mobile(value) if value else None


class AddressFieldsIn(StrictIn):
    """A validated Indian postal address (shared by the address book and checkout)."""

    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(max_length=20)
    line1: str = Field(min_length=3, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    landmark: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    state: str
    pincode: str

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalise_indian_mobile(value)

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        if value not in INDIAN_STATES:
            raise ValueError("Choose a state or union territory from the list.")
        return value

    @field_validator("pincode")
    @classmethod
    def _pincode(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[1-9][0-9]{5}", value):
            raise ValueError("Enter a valid 6-digit PIN code.")
        return value


class AddressIn(AddressFieldsIn):
    label: str | None = Field(default=None, max_length=40)
    is_default_shipping: bool = False
    is_default_billing: bool = False


class AddressOut(BaseModel):
    id: str
    label: str | None
    full_name: str
    phone: str
    line1: str
    line2: str | None
    landmark: str | None
    city: str
    state: str
    pincode: str
    country: str
    is_default_shipping: bool
    is_default_billing: bool


class WishlistMergeIn(StrictIn):
    slugs: list[str] = Field(max_length=50)
