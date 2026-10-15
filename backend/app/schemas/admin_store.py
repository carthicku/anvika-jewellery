"""Admin requests/responses for promotions, shipping, content, enquiries, settings and staff."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.money import MoneyStr
from app.schemas.common import StrictIn

# --------------------------------------------------------------------------------------------
# Automatic discounts
# --------------------------------------------------------------------------------------------


class DiscountIn(StrictIn):
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["percent_off_making", "percent_off_price", "flat_off_price"]
    value: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    scope: Literal["all", "category", "collection", "product"] = "all"
    scope_id: uuid.UUID | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _rules(self) -> DiscountIn:
        if self.kind != "flat_off_price" and self.value > 100:
            raise ValueError("A percentage discount can't be above 100%.")
        if self.scope == "all":
            self.scope_id = None
        elif self.scope_id is None:
            raise ValueError("Choose what this discount applies to.")
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("The end must be after the start.")
        return self


class DiscountOut(BaseModel):
    id: str
    name: str
    kind: str
    value: MoneyStr
    scope: str
    scope_id: str | None
    scope_name: str | None
    starts_at: datetime
    ends_at: datetime | None
    is_active: bool
    running_now: bool


# --------------------------------------------------------------------------------------------
# Coupons
# --------------------------------------------------------------------------------------------


class CouponUpdateIn(StrictIn):
    description: str | None = Field(default=None, max_length=200)
    kind: Literal["percent", "flat"]
    value: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    max_discount_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    min_order_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    starts_at: datetime
    ends_at: datetime | None = None
    usage_limit_total: int | None = Field(default=None, ge=1, le=1_000_000)
    usage_limit_per_customer: int | None = Field(default=None, ge=1, le=1000)
    is_active: bool = True

    @model_validator(mode="after")
    def _rules(self) -> CouponUpdateIn:
        if self.kind == "percent" and self.value > 100:
            raise ValueError("A percentage coupon can't be above 100%.")
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("The end must be after the start.")
        return self


class CouponCreateIn(CouponUpdateIn):
    code: str

    @field_validator("code")
    @classmethod
    def _code(cls, value: str) -> str:
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{3,40}", value):
            raise ValueError("Use 3–40 letters or numbers, no spaces.")
        return value


class CouponOut(BaseModel):
    id: str
    code: str
    description: str | None
    kind: str
    value: MoneyStr
    max_discount_amount: MoneyStr | None
    min_order_amount: MoneyStr | None
    starts_at: datetime
    ends_at: datetime | None
    usage_limit_total: int | None
    usage_limit_per_customer: int | None
    is_active: bool
    is_sample: bool
    times_used: int
    times_reserved: int


# --------------------------------------------------------------------------------------------
# Shipping
# --------------------------------------------------------------------------------------------


class ShippingMethodIn(StrictIn):
    code: str = Field(pattern=r"^[a-z0-9_-]{2,40}$")
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    fee: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    free_above: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    min_days: int = Field(ge=0, le=60)
    max_days: int = Field(ge=0, le=90)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0, le=1000)

    @model_validator(mode="after")
    def _days(self) -> ShippingMethodIn:
        if self.max_days < self.min_days:
            raise ValueError("Maximum days can't be less than minimum days.")
        return self


class ShippingMethodOut(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    fee: MoneyStr
    free_above: MoneyStr | None
    min_days: int
    max_days: int
    is_active: bool
    sort_order: int


class ShippingZoneIn(StrictIn):
    name: str = Field(min_length=2, max_length=80)
    pincode_prefixes: list[str] = Field(min_length=1, max_length=500)
    extra_days: int = Field(default=0, ge=0, le=30)
    is_active: bool = True

    @field_validator("pincode_prefixes")
    @classmethod
    def _prefixes(cls, values: list[str]) -> list[str]:
        cleaned = sorted({v.strip() for v in values if v.strip()})
        for v in cleaned:
            if not re.fullmatch(r"[1-9][0-9]{0,5}", v):
                raise ValueError(f"'{v}' isn't a PIN code or PIN-code prefix (1–6 digits).")
        if not cleaned:
            raise ValueError("Add at least one PIN code or prefix.")
        return cleaned


class ShippingZoneOut(BaseModel):
    id: str
    name: str
    pincode_prefixes: list[str]
    extra_days: int
    is_active: bool


# --------------------------------------------------------------------------------------------
# Content, enquiries, newsletter
# --------------------------------------------------------------------------------------------


class ContentPageIn(StrictIn):
    title: str = Field(min_length=2, max_length=160)
    summary: str | None = Field(default=None, max_length=300)
    body_markdown: str = Field(max_length=100_000)
    is_draft_template: bool


class AdminContentPageOut(BaseModel):
    slug: str
    title: str
    summary: str | None
    body_markdown: str
    is_draft_template: bool
    updated_at: datetime


class EnquiryOut(BaseModel):
    id: str
    name: str
    email: str
    phone: str | None
    subject: str
    message: str
    status: str
    created_at: datetime


class EnquiryStatusIn(StrictIn):
    status: Literal["new", "in_progress", "closed"]


class SubscriberOut(BaseModel):
    email: str
    status: str
    source: str | None
    consent_at: datetime
    unsubscribed_at: datetime | None


# --------------------------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------------------------

GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


class StoreSettingsIn(StrictIn):
    tagline: str = Field(max_length=120)
    support_email: str = Field(max_length=254)
    support_phone: str = Field(max_length=60)
    whatsapp: str | None = Field(default=None, max_length=60)
    business_address: str = Field(max_length=500)
    gstin: str = Field(max_length=40)
    business_hours: str = Field(max_length=200)

    @field_validator("gstin")
    @classmethod
    def _gstin(cls, value: str) -> str:
        value = value.strip().upper() if not value.startswith("[") else value
        if not value.startswith("[") and not GSTIN_RE.match(value):
            raise ValueError("Enter a 15-character GSTIN (e.g. 29ABCDE1234F1Z5).")
        return value

    @field_validator("support_email")
    @classmethod
    def _email(cls, value: str) -> str:
        if not value.startswith("[") and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class AnnouncementIn(StrictIn):
    enabled: bool
    text: str = Field(max_length=160)
    link: str | None = Field(default=None, max_length=300)

    @field_validator("link")
    @classmethod
    def _link(cls, value: str | None) -> str | None:
        if value and not (value.startswith("/") or value.startswith("https://")):
            raise ValueError("Use a site path like /collections or a full https:// link.")
        if value and value.startswith("//"):
            raise ValueError("Use a site path like /collections or a full https:// link.")
        return value or None


class TaxIn(StrictIn):
    metal_percent: Decimal = Field(ge=0, le=28, max_digits=5, decimal_places=2)
    making_percent: Decimal = Field(ge=0, le=28, max_digits=5, decimal_places=2)
    stones_percent: Decimal = Field(ge=0, le=28, max_digits=5, decimal_places=2)
    shipping_percent: Decimal = Field(ge=0, le=28, max_digits=5, decimal_places=2)


class PricingPolicyIn(StrictIn):
    gold_rate_max_change_percent: Decimal = Field(ge=Decimal("0.5"), le=50, decimal_places=2)
    gold_rate_stale_after_hours: int = Field(ge=1, le=720)
    block_checkout_when_rate_stale: bool


class SettingsOut(BaseModel):
    store: StoreSettingsIn
    announcement: AnnouncementIn
    tax: TaxIn
    pricing_policy: PricingPolicyIn


# --------------------------------------------------------------------------------------------
# Staff users
# --------------------------------------------------------------------------------------------


class StaffUserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: Literal["customer", "staff", "admin"]
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class RoleIn(StrictIn):
    role: Literal["customer", "staff", "admin"]


class PromoteIn(StrictIn):
    email: str = Field(max_length=254)
    role: Literal["staff", "admin"]


class ActiveIn(StrictIn):
    is_active: bool
