"""Loads what the pure pricing engine needs from the database: current gold rates, tax settings,
active discounts and collection memberships. See docs/architecture/PRICING_ENGINE.md §1.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import Category, CollectionProduct, Discount, GoldRate, Product, ProductVariant
from app.services import store_settings
from app.services.pricing import (
    DiscountInput,
    GoldRateInput,
    ProductPricing,
    TaxRates,
    UnitPrice,
    VariantPricing,
    price_unit,
)


def current_gold_rates(db: Session, now: datetime | None = None) -> dict[str, GoldRate]:
    """Latest rate per purity whose effective_from is not in the future."""
    now = now or utcnow()
    rows = db.scalars(
        select(GoldRate)
        .where(GoldRate.effective_from <= now)
        .order_by(GoldRate.purity, GoldRate.effective_from.desc(), GoldRate.created_at.desc())
        .ext(distinct_on(GoldRate.purity))
    ).all()
    return {row.purity: row for row in rows}


def active_discounts(db: Session, now: datetime | None = None) -> list[Discount]:
    now = now or utcnow()
    return list(
        db.scalars(
            select(Discount)
            .where(
                Discount.is_active.is_(True),
                Discount.starts_at <= now,
                or_(Discount.ends_at.is_(None), Discount.ends_at > now),
            )
            .order_by(Discount.created_at, Discount.id)
        ).all()
    )


def product_pricing(product: Product) -> ProductPricing:
    return ProductPricing(
        pricing_model=product.pricing_model,
        purity=product.purity,
        making_charge_type=product.making_charge_type,
        making_charge_value=product.making_charge_value,
        wastage_percent=product.wastage_percent,
    )


def variant_pricing(variant: ProductVariant) -> VariantPricing:
    return VariantPricing(
        net_gold_weight_g=variant.net_gold_weight_g,
        fixed_price=variant.fixed_price,
        stone_value=variant.stone_value,
        other_charges=variant.other_charges,
    )


@dataclass
class PricingContext:
    tax: TaxRates
    rates: dict[str, GoldRate]
    discounts: list[Discount]
    collections_by_product: dict[uuid.UUID, set[uuid.UUID]] = field(default_factory=dict)
    category_parent: dict[uuid.UUID, uuid.UUID | None] = field(default_factory=dict)

    def rate_for(self, purity: str) -> GoldRateInput | None:
        rate = self.rates.get(purity)
        return GoldRateInput(rate.id, rate.purity, rate.rate_per_gram) if rate else None

    def discounts_for(self, product: Product) -> list[DiscountInput]:
        categories = {product.category_id}
        parent = self.category_parent.get(product.category_id)
        if parent:
            categories.add(parent)
        collections = self.collections_by_product.get(product.id, set())
        applicable = []
        for d in self.discounts:
            if (
                d.scope == "all"
                or (d.scope == "product" and d.scope_id == product.id)
                or (d.scope == "category" and d.scope_id in categories)
                or (d.scope == "collection" and d.scope_id in collections)
            ):
                applicable.append(DiscountInput(d.id, d.name, d.kind, d.value))
        return applicable

    def price(self, product: Product, variant: ProductVariant) -> UnitPrice:
        """Price one piece. Raises pricing.PriceUnavailable when it cannot be sold."""
        return price_unit(
            product_pricing(product),
            variant_pricing(variant),
            self.rate_for(product.purity) if product.pricing_model == "weight_based" else None,
            self.tax,
            self.discounts_for(product),
        )


def load_pricing_context(
    db: Session, products: Sequence[Product], now: datetime | None = None
) -> PricingContext:
    """Everything needed to price `products`, loaded with a handful of queries."""
    now = now or utcnow()
    product_ids = [p.id for p in products]
    collections: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    if product_ids:
        for product_id, collection_id in db.execute(
            select(CollectionProduct.product_id, CollectionProduct.collection_id).where(
                CollectionProduct.product_id.in_(product_ids)
            )
        ):
            collections[product_id].add(collection_id)
    category_ids = {p.category_id for p in products}
    parents: dict[uuid.UUID, uuid.UUID | None] = {}
    if category_ids:
        parents = {
            row.id: row.parent_id
            for row in db.execute(
                select(Category.id, Category.parent_id).where(Category.id.in_(category_ids))
            )
        }
    return PricingContext(
        tax=store_settings.get_tax_rates(db),
        rates=current_gold_rates(db, now),
        discounts=active_discounts(db, now),
        collections_by_product=dict(collections),
        category_parent=parents,
    )
