"""Public catalogue responses. Prices come from the pricing engine — never computed by clients."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.core.money import MoneyStr
from app.schemas.common import WeightStr

StockStatusOut = Literal["in_stock", "low_stock", "out_of_stock"]


class ImageOut(BaseModel):
    url: str
    alt: str
    width: int | None = None
    height: int | None = None
    renditions: dict[str, str] = {}
    is_placeholder: bool = False


class CategoryRef(BaseModel):
    slug: str
    name: str


class PriceRowOut(BaseModel):
    key: str
    label: str
    amount: MoneyStr


class GoldRateRef(BaseModel):
    purity: str
    rate_per_gram: MoneyStr
    effective_from: datetime


class PriceOut(BaseModel):
    """One piece, tax included. `available=False` means the item cannot be priced or sold now."""

    available: bool
    unavailable_reason: str | None = None
    currency: Literal["INR"] = "INR"
    amount: MoneyStr | None = None
    compare_at: MoneyStr | None = None
    discount_label: str | None = None
    breakdown: list[PriceRowOut] = []
    gold_rate: GoldRateRef | None = None


class ProductCardOut(BaseModel):
    id: str
    slug: str
    name: str
    category: CategoryRef
    purity: str
    metal_colour: str
    weight_g: WeightStr | None
    image: ImageOut | None
    hover_image: ImageOut | None
    price: PriceOut
    stock_status: StockStatusOut
    is_sample: bool
    is_new: bool


class VariantOut(BaseModel):
    id: str
    sku: str
    label: str
    size: str | None
    gross_weight_g: WeightStr | None
    net_gold_weight_g: WeightStr | None
    stone_weight_ct: WeightStr | None
    is_default: bool
    stock_status: StockStatusOut
    # Capped at 10 (the per-line purchase limit) so exact stock of larger lots is not exposed.
    available_quantity: int
    price: PriceOut


class AttributeOut(BaseModel):
    key: str
    value: str


class CollectionRef(BaseModel):
    slug: str
    name: str


class ProductDetailOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str | None
    category: CategoryRef
    parent_category: CategoryRef | None
    collections: list[CollectionRef]
    purity: str
    metal_colour: str
    pricing_model: str
    stone_details: str | None
    hallmark_details: str | None
    certification_details: str | None
    care_instructions: str | None
    return_eligible: bool
    exchange_eligible: bool
    return_window_days: int | None
    images: list[ImageOut]
    variants: list[VariantOut]
    attributes: list[AttributeOut]
    is_sample: bool
    seo_title: str | None
    seo_description: str | None
    published_at: datetime | None


class CategoryOut(BaseModel):
    slug: str
    name: str
    description: str | None
    image_url: str | None
    parent_slug: str | None
    seo_title: str | None
    seo_description: str | None


class CollectionOut(BaseModel):
    slug: str
    name: str
    description: str | None
    hero_image_url: str | None
    is_featured: bool
    seo_title: str | None
    seo_description: str | None


class FacetValueOut(BaseModel):
    value: str
    label: str
    count: int


class FacetsOut(BaseModel):
    total: int
    categories: list[FacetValueOut]
    purities: list[FacetValueOut]
    metal_colours: list[FacetValueOut]
    attributes: dict[str, list[FacetValueOut]]
    price_min: MoneyStr | None
    price_max: MoneyStr | None
    in_stock_count: int


class HomeOut(BaseModel):
    categories: list[CategoryOut]
    collections: list[CollectionOut]
    new_arrivals: list[ProductCardOut]
    featured: list[ProductCardOut]
    bestsellers: list[ProductCardOut]


class SuggestionProductOut(BaseModel):
    slug: str
    name: str
    image: ImageOut | None
    price: PriceOut


class SuggestOut(BaseModel):
    products: list[SuggestionProductOut]
    categories: list[CategoryRef]
