"""Catalogue: categories, collections, products, variants, images, attributes."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey, enum_check
from app.models.enums import (
    MAKING_CHARGE_TYPES,
    METAL_COLOURS,
    PRICING_MODELS,
    PRODUCT_STATUSES,
    PURITIES,
)


class Category(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "categories"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    seo_title: Mapped[str | None] = mapped_column(String(120))
    seo_description: Mapped[str | None] = mapped_column(String(300))

    parent: Mapped[Category | None] = relationship(remote_side="Category.id")


class Collection(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "collections"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    hero_image_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seo_title: Mapped[str | None] = mapped_column(String(120))
    seo_description: Mapped[str | None] = mapped_column(String(300))


class CollectionProduct(Base):
    __tablename__ = "collection_products"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english', coalesce(name, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(description, '')), 'B')"
)


class Product(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(enum_check("status", PRODUCT_STATUSES), name="status"),
        CheckConstraint(enum_check("purity", PURITIES), name="purity"),
        CheckConstraint(enum_check("metal_colour", METAL_COLOURS), name="metal_colour"),
        CheckConstraint(enum_check("pricing_model", PRICING_MODELS), name="pricing_model"),
        CheckConstraint(
            enum_check("making_charge_type", MAKING_CHARGE_TYPES), name="making_charge_type"
        ),
        CheckConstraint("making_charge_value >= 0", name="making_charge_value_non_negative"),
        CheckConstraint(
            "wastage_percent IS NULL OR (wastage_percent >= 0 AND wastage_percent <= 100)",
            name="wastage_percent_range",
        ),
        CheckConstraint(
            "return_window_days IS NULL OR return_window_days BETWEEN 0 AND 365",
            name="return_window_days_range",
        ),
        Index("ix_products_status_category", "status", "category_id"),
        Index("ix_products_published_at", "published_at"),
        Index("ix_products_price_from", "price_from"),
        Index("ix_products_search_vector", "search_vector", postgresql_using="gin"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    metal_colour: Mapped[str] = mapped_column(String(16), nullable=False, default="yellow")
    purity: Mapped[str] = mapped_column(String(4), nullable=False)
    pricing_model: Mapped[str] = mapped_column(String(16), nullable=False)
    making_charge_type: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    making_charge_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    wastage_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))

    description: Mapped[str | None] = mapped_column(Text)
    stone_details: Mapped[str | None] = mapped_column(Text)
    hallmark_details: Mapped[str | None] = mapped_column(Text)
    certification_details: Mapped[str | None] = mapped_column(Text)
    care_instructions: Mapped[str | None] = mapped_column(Text)

    return_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exchange_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    return_window_days: Mapped[int | None] = mapped_column(Integer)

    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_bestseller: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    seo_title: Mapped[str | None] = mapped_column(String(120))
    seo_description: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Listing cache — lowest purchasable variant price, used ONLY for SQL sorting/filtering.
    # Displayed and charged prices are always computed live (PRICING_ENGINE.md §8).
    price_from: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    price_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed(SEARCH_VECTOR_SQL, persisted=True), nullable=True
    )

    category: Mapped[Category] = relationship()
    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product",
        order_by="ProductVariant.sort_order",
        cascade="all, delete-orphan",
    )
    images: Mapped[list[ProductImage]] = relationship(
        order_by="ProductImage.sort_order", cascade="all, delete-orphan"
    )
    attributes: Mapped[list[ProductAttribute]] = relationship(cascade="all, delete-orphan")


class ProductVariant(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint(
            "gross_weight_g IS NULL OR gross_weight_g > 0", name="gross_weight_positive"
        ),
        CheckConstraint(
            "net_gold_weight_g IS NULL OR net_gold_weight_g > 0", name="net_weight_positive"
        ),
        CheckConstraint(
            "net_gold_weight_g IS NULL OR gross_weight_g IS NULL "
            "OR net_gold_weight_g <= gross_weight_g",
            name="net_not_above_gross",
        ),
        CheckConstraint("stone_value >= 0 AND other_charges >= 0", name="charges_non_negative"),
        CheckConstraint("fixed_price IS NULL OR fixed_price >= 0", name="fixed_price_non_negative"),
        Index("ix_product_variants_product_id", "product_id"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="Standard")
    size: Mapped[str | None] = mapped_column(String(20))
    gross_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    net_gold_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    stone_weight_ct: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    stone_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal(0))
    other_charges: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal(0)
    )
    other_charges_label: Mapped[str | None] = mapped_column(String(80))
    fixed_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    huid: Mapped[str | None] = mapped_column(String(12))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    product: Mapped[Product] = relationship(back_populates="variants")


class ProductImage(UUIDPrimaryKey, Base):
    __tablename__ = "product_images"
    __table_args__ = (Index("ix_product_images_product_id", "product_id"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(300))
    # Responsive renditions {"400": url, "800": url, ...}; empty for vector placeholders.
    renditions: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    alt_text: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProductAttribute(UUIDPrimaryKey, Base):
    __tablename__ = "product_attributes"
    __table_args__ = (
        UniqueConstraint("product_id", "key", "value"),
        Index("ix_product_attributes_key_value", "key", "value"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[str] = mapped_column(String(80), nullable=False)
