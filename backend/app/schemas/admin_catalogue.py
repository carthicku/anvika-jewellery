"""Admin catalogue requests/responses: products, variants, images, categories, collections and the
live price preview. Prices are never stored from the form — only pricing INPUTS (weights, making
charges, fixed pre-tax prices); the engine calculates what customers pay."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.money import MoneyStr
from app.schemas.catalogue import ImageOut, PriceRowOut
from app.schemas.common import StrictIn, WeightStr

Purity = Literal["24K", "22K", "18K", "14K"]
ProductStatus = Literal["draft", "active", "archived"]
MetalColour = Literal["yellow", "white", "rose", "two_tone"]
PricingModel = Literal["fixed", "weight_based"]
MakingType = Literal["per_gram", "percent", "flat", "none"]

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKU_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,39}$")

NonNegativeMoney = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=2)


def check_slug(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not SLUG_RE.match(value) or len(value) > 100:
        raise ValueError("Use lowercase letters, numbers and single hyphens (e.g. gold-hoops).")
    return value


class AttributeIn(StrictIn):
    key: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=80)


class VariantIn(StrictIn):
    sku: str
    label: str = Field(default="Standard", min_length=1, max_length=80)
    size: str | None = Field(default=None, max_length=20)
    gross_weight_g: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    net_gold_weight_g: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    stone_weight_ct: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=3)
    stone_value: Decimal = NonNegativeMoney
    other_charges: Decimal = NonNegativeMoney
    other_charges_label: str | None = Field(default=None, max_length=80)
    fixed_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    huid: str | None = Field(
        default=None, description="BIS hallmark unique ID, if the owner records it"
    )
    is_default: bool = False
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0, le=1000)

    @field_validator("sku")
    @classmethod
    def _sku(cls, value: str) -> str:
        value = value.strip().upper()
        if not SKU_RE.match(value):
            raise ValueError("SKU: 3–40 capital letters, numbers or hyphens.")
        return value

    @field_validator("huid")
    @classmethod
    def _huid(cls, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{6}", value):
            raise ValueError("HUID is 6 letters or numbers.")
        return value

    @model_validator(mode="after")
    def _weights(self) -> VariantIn:
        if (
            self.gross_weight_g is not None
            and self.net_gold_weight_g is not None
            and self.net_gold_weight_g > self.gross_weight_g
        ):
            raise ValueError("Net gold weight can't be more than the gross weight.")
        return self


class VariantCreateIn(VariantIn):
    initial_stock: int = Field(default=0, ge=0, le=10_000)


class ProductIn(StrictIn):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = None
    category_id: uuid.UUID
    status: ProductStatus = "draft"
    metal_colour: MetalColour = "yellow"
    purity: Purity
    pricing_model: PricingModel
    making_charge_type: MakingType = "none"
    making_charge_value: Decimal = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=2)
    wastage_percent: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=6, decimal_places=3
    )
    description: str | None = Field(default=None, max_length=5000)
    stone_details: str | None = Field(default=None, max_length=2000)
    hallmark_details: str | None = Field(default=None, max_length=2000)
    certification_details: str | None = Field(default=None, max_length=2000)
    care_instructions: str | None = Field(default=None, max_length=2000)
    return_eligible: bool = False
    exchange_eligible: bool = False
    return_window_days: int | None = Field(default=None, ge=0, le=365)
    is_featured: bool = False
    is_bestseller: bool = False
    seo_title: str | None = Field(default=None, max_length=120)
    seo_description: str | None = Field(default=None, max_length=300)
    attributes: list[AttributeIn] = Field(default_factory=list, max_length=30)
    collection_ids: list[uuid.UUID] = Field(default_factory=list, max_length=30)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        return check_slug(value)

    @model_validator(mode="after")
    def _making(self) -> ProductIn:
        if self.making_charge_type == "percent" and self.making_charge_value > 100:
            raise ValueError("A percentage making charge can't be above 100%.")
        if self.making_charge_type == "none" and self.making_charge_value:
            self.making_charge_value = Decimal(0)
        return self


class ProductCreateIn(ProductIn):
    variants: list[VariantCreateIn] = Field(min_length=1, max_length=50)


class ProductRowOut(BaseModel):
    id: str
    name: str
    slug: str
    status: ProductStatus
    category: str
    purity: Purity
    pricing_model: PricingModel
    variant_count: int
    available: int
    price_from: MoneyStr | None
    image: ImageOut | None
    is_sample: bool
    updated_at: datetime


class AdminVariantOut(BaseModel):
    id: str
    sku: str
    label: str
    size: str | None
    gross_weight_g: WeightStr | None
    net_gold_weight_g: WeightStr | None
    stone_weight_ct: WeightStr | None
    stone_value: MoneyStr
    other_charges: MoneyStr
    other_charges_label: str | None
    fixed_price: MoneyStr | None
    huid: str | None
    is_default: bool
    is_active: bool
    sort_order: int
    on_hand: int
    reserved: int
    unit_price: MoneyStr | None
    price_error: str | None


class AdminImageOut(BaseModel):
    id: str
    url: str
    alt_text: str
    width: int | None
    height: int | None
    renditions: dict[str, str]
    sort_order: int
    is_placeholder: bool


class AdminProductOut(BaseModel):
    id: str
    name: str
    slug: str
    category_id: str
    status: ProductStatus
    metal_colour: MetalColour
    purity: Purity
    pricing_model: PricingModel
    making_charge_type: MakingType
    making_charge_value: MoneyStr
    wastage_percent: Decimal | None
    description: str | None
    stone_details: str | None
    hallmark_details: str | None
    certification_details: str | None
    care_instructions: str | None
    return_eligible: bool
    exchange_eligible: bool
    return_window_days: int | None
    is_featured: bool
    is_bestseller: bool
    is_sample: bool
    seo_title: str | None
    seo_description: str | None
    attributes: list[AttributeIn]
    collection_ids: list[str]
    variants: list[AdminVariantOut]
    images: list[AdminImageOut]
    publish_problems: list[str]
    published_at: datetime | None
    updated_at: datetime


class ImageUpdateIn(StrictIn):
    alt_text: str = Field(max_length=200)


class ImageOrderIn(StrictIn):
    image_ids: list[uuid.UUID] = Field(min_length=1, max_length=30)


# --------------------------------------------------------------------------------------------
# Price preview (no saving)
# --------------------------------------------------------------------------------------------


class PreviewVariantIn(StrictIn):
    label: str = Field(default="Standard", max_length=80)
    net_gold_weight_g: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    fixed_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stone_value: Decimal = NonNegativeMoney
    other_charges: Decimal = NonNegativeMoney


class PricePreviewIn(StrictIn):
    purity: Purity
    pricing_model: PricingModel
    making_charge_type: MakingType = "none"
    making_charge_value: Decimal = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=2)
    wastage_percent: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=6, decimal_places=3
    )
    variants: list[PreviewVariantIn] = Field(min_length=1, max_length=50)


class VariantPriceOut(BaseModel):
    label: str
    total: MoneyStr | None
    breakdown: list[PriceRowOut]
    error: str | None


class PricePreviewOut(BaseModel):
    gold_rate_per_gram: MoneyStr | None
    variants: list[VariantPriceOut]
    note: str


# --------------------------------------------------------------------------------------------
# Categories and collections
# --------------------------------------------------------------------------------------------


class CategoryIn(StrictIn):
    name: str = Field(min_length=2, max_length=80)
    slug: str | None = None
    parent_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0, le=1000)
    is_active: bool = True
    seo_title: str | None = Field(default=None, max_length=120)
    seo_description: str | None = Field(default=None, max_length=300)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        return check_slug(value)


class AdminCategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    parent_id: str | None
    description: str | None
    sort_order: int
    is_active: bool
    seo_title: str | None
    seo_description: str | None
    product_count: int


class CollectionIn(StrictIn):
    name: str = Field(min_length=2, max_length=80)
    slug: str | None = None
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = Field(default=0, ge=0, le=1000)
    seo_title: str | None = Field(default=None, max_length=120)
    seo_description: str | None = Field(default=None, max_length=300)
    product_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        return check_slug(value)


class AdminCollectionOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    is_active: bool
    is_featured: bool
    sort_order: int
    seo_title: str | None
    seo_description: str | None
    product_ids: list[str]
