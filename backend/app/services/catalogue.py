"""Public catalogue queries: listing with filters/sort/search/pagination, facets, product detail,
related products, home page data, search suggestions, and the listing price cache.

Only `active` products are ever returned by these functions.
"""

from __future__ import annotations

import math
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, exists, func, literal, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFound
from app.core.time import utcnow
from app.models import (
    Category,
    Collection,
    CollectionProduct,
    InventoryLevel,
    Product,
    ProductAttribute,
    ProductImage,
    ProductVariant,
)
from app.schemas.catalogue import (
    AttributeOut,
    CategoryOut,
    CategoryRef,
    CollectionOut,
    CollectionRef,
    FacetsOut,
    FacetValueOut,
    GoldRateRef,
    HomeOut,
    ImageOut,
    PriceOut,
    PriceRowOut,
    ProductCardOut,
    ProductDetailOut,
    SuggestionProductOut,
    SuggestOut,
    VariantOut,
)
from app.services import inventory
from app.services.pricing import PriceUnavailable, UnitPrice, unit_breakdown
from app.services.pricing_context import PricingContext, load_pricing_context

SORTS = ("relevance", "newest", "price_asc", "price_desc")
MAX_QUERY_LENGTH = 100
NEW_ARRIVAL_DAYS = 45
PURITY_LABELS = {"24K": "24K", "22K": "22K", "18K": "18K", "14K": "14K"}
METAL_LABELS = {
    "yellow": "Yellow gold",
    "white": "White gold",
    "rose": "Rose gold",
    "two_tone": "Two-tone",
}
PURCHASE_LIMIT = 10


@dataclass
class ProductFilters:
    q: str | None = None
    category: str | None = None
    collection: str | None = None
    purity: list[str] = field(default_factory=list)
    metal_colour: list[str] = field(default_factory=list)
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    in_stock: bool = False
    attributes: dict[str, list[str]] = field(default_factory=dict)
    sort: str = "relevance"
    page: int = 1
    page_size: int = 24


# --------------------------------------------------------------------------------------------
# Query building
# --------------------------------------------------------------------------------------------


def normalise_query(raw: str | None) -> str | None:
    """Trim, collapse whitespace, drop control characters, cap length. Empty → None."""
    if raw is None:
        return None
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()[:MAX_QUERY_LENGTH]
    return cleaned or None


def _like_pattern(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _tsquery(q: str) -> ColumnElement[Any]:
    return func.websearch_to_tsquery("english", q)


def _search_condition(q: str) -> ColumnElement[bool]:
    pattern = _like_pattern(q)
    sku_match = exists().where(
        ProductVariant.product_id == Product.id, ProductVariant.sku.ilike(pattern, escape="\\")
    )
    category_match = exists().where(
        Category.id == Product.category_id, Category.name.ilike(pattern, escape="\\")
    )
    return or_(
        Product.search_vector.op("@@")(_tsquery(q)),
        Product.name.ilike(pattern, escape="\\"),
        sku_match,
        category_match,
    )


def _in_stock_condition() -> ColumnElement[bool]:
    return exists().where(
        ProductVariant.product_id == Product.id,
        ProductVariant.is_active.is_(True),
        InventoryLevel.variant_id == ProductVariant.id,
        InventoryLevel.on_hand - InventoryLevel.reserved > 0,
    )


def _category_ids(db: Session, slug: str) -> list[uuid.UUID]:
    category = db.scalar(select(Category).where(Category.slug == slug, Category.is_active))
    if category is None:
        raise NotFound("We couldn't find that category.")
    children = db.scalars(
        select(Category.id).where(Category.parent_id == category.id, Category.is_active)
    ).all()
    return [category.id, *children]


def _collection_id(db: Session, slug: str) -> uuid.UUID:
    collection_id = db.scalar(
        select(Collection.id).where(Collection.slug == slug, Collection.is_active)
    )
    if collection_id is None:
        raise NotFound("We couldn't find that collection.")
    return collection_id


def _context_conditions(db: Session, f: ProductFilters) -> list[ColumnElement[bool]]:
    """Filters that define the browsing context (used for facets too)."""
    conditions: list[ColumnElement[bool]] = [Product.status == "active"]
    if f.q:
        conditions.append(_search_condition(f.q))
    if f.category:
        conditions.append(Product.category_id.in_(_category_ids(db, f.category)))
    if f.collection:
        collection_id = _collection_id(db, f.collection)
        conditions.append(
            exists().where(
                CollectionProduct.product_id == Product.id,
                CollectionProduct.collection_id == collection_id,
            )
        )
    return conditions


def _refinement_conditions(f: ProductFilters) -> list[ColumnElement[bool]]:
    """Filters the shopper toggles inside a context."""
    conditions: list[ColumnElement[bool]] = []
    if f.purity:
        conditions.append(Product.purity.in_(f.purity))
    if f.metal_colour:
        conditions.append(Product.metal_colour.in_(f.metal_colour))
    if f.min_price is not None:
        conditions.append(Product.price_from >= f.min_price)
    if f.max_price is not None:
        conditions.append(Product.price_from <= f.max_price)
    if f.in_stock:
        conditions.append(_in_stock_condition())
    for key, values in f.attributes.items():
        if values:
            conditions.append(
                exists().where(
                    ProductAttribute.product_id == Product.id,
                    ProductAttribute.key == key,
                    ProductAttribute.value.in_(values),
                )
            )
    return conditions


def _apply_sort(stmt: Select[Any], f: ProductFilters) -> Select[Any]:
    if f.sort == "newest":
        return stmt.order_by(Product.published_at.desc().nulls_last(), Product.id)
    if f.sort == "price_asc":
        return stmt.order_by(Product.price_from.asc().nulls_last(), Product.id)
    if f.sort == "price_desc":
        return stmt.order_by(Product.price_from.desc().nulls_last(), Product.id)
    if f.q:
        rank = func.ts_rank(Product.search_vector, _tsquery(f.q))
        name_hit = Product.name.ilike(_like_pattern(f.q), escape="\\")
        return stmt.order_by(name_hit.desc(), rank.desc(), Product.name, Product.id)
    # "relevance" without a query = curated order: featured first, then newest.
    return stmt.order_by(
        Product.is_featured.desc(), Product.published_at.desc().nulls_last(), Product.id
    )


def _load_products(db: Session, ids: Sequence[uuid.UUID]) -> list[Product]:
    if not ids:
        return []
    rows = db.scalars(
        select(Product)
        .where(Product.id.in_(ids))
        .options(
            selectinload(Product.variants),
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.attributes),
        )
    ).all()
    by_id = {p.id: p for p in rows}
    return [by_id[i] for i in ids if i in by_id]


# --------------------------------------------------------------------------------------------
# Serialisation helpers
# --------------------------------------------------------------------------------------------


def image_out(image: ProductImage) -> ImageOut:
    return ImageOut(
        url=image.url,
        alt=image.alt_text,
        width=image.width,
        height=image.height,
        renditions=image.renditions or {},
        is_placeholder=image.is_placeholder,
    )


def price_out(
    ctx: PricingContext, product: Product, variant: ProductVariant, *, with_breakdown: bool
) -> tuple[PriceOut, UnitPrice | None]:
    try:
        unit = ctx.price(product, variant)
    except PriceUnavailable as exc:
        return PriceOut(available=False, unavailable_reason=exc.reason), None
    rate = ctx.rates.get(product.purity) if product.pricing_model == "weight_based" else None
    return (
        PriceOut(
            available=True,
            amount=unit.total,
            compare_at=unit.total_before_discount if unit.discount else None,
            discount_label=unit.discount.name if unit.discount else None,
            breakdown=[PriceRowOut(**row) for row in unit_breakdown(unit)]
            if with_breakdown
            else [],
            gold_rate=(
                GoldRateRef(
                    purity=rate.purity,
                    rate_per_gram=rate.rate_per_gram,
                    effective_from=rate.effective_from,
                )
                if rate and with_breakdown
                else None
            ),
        ),
        unit,
    )


def _active_variants(product: Product) -> list[ProductVariant]:
    return [v for v in product.variants if v.is_active]


def _cheapest_variant(
    ctx: PricingContext, product: Product
) -> tuple[ProductVariant | None, PriceOut]:
    best: tuple[ProductVariant, PriceOut, Decimal] | None = None
    fallback: tuple[ProductVariant, PriceOut] | None = None
    for variant in _active_variants(product):
        out, unit = price_out(ctx, product, variant, with_breakdown=False)
        if unit is None:
            fallback = fallback or (variant, out)
            continue
        if best is None or unit.total < best[2]:
            best = (variant, out, unit.total)
    if best:
        return best[0], best[1]
    if fallback:
        return fallback
    return None, PriceOut(available=False, unavailable_reason="NO_VARIANTS")


def cards(db: Session, products: Sequence[Product]) -> list[ProductCardOut]:
    if not products:
        return []
    ctx = load_pricing_context(db, products)
    levels = inventory.levels_for(db, [v.id for p in products for v in p.variants])
    now = utcnow()
    result = []
    for product in products:
        variant, price = _cheapest_variant(ctx, product)
        statuses = [inventory.stock_status(levels.get(v.id)) for v in _active_variants(product)]
        stock = (
            "in_stock"
            if "in_stock" in statuses
            else "low_stock"
            if "low_stock" in statuses
            else "out_of_stock"
        )
        default = next((v for v in product.variants if v.is_default), variant)
        images = product.images
        result.append(
            ProductCardOut(
                id=str(product.id),
                slug=product.slug,
                name=product.name,
                category=CategoryRef(slug=product.category.slug, name=product.category.name),
                purity=product.purity,
                metal_colour=product.metal_colour,
                weight_g=default.gross_weight_g if default else None,
                image=image_out(images[0]) if images else None,
                hover_image=image_out(images[1]) if len(images) > 1 else None,
                price=price,
                stock_status=stock,
                is_sample=product.is_sample,
                is_new=bool(
                    product.published_at
                    and product.published_at >= now - timedelta(days=NEW_ARRIVAL_DAYS)
                ),
            )
        )
    return result


# --------------------------------------------------------------------------------------------
# Public operations
# --------------------------------------------------------------------------------------------


def list_products(db: Session, f: ProductFilters) -> tuple[list[ProductCardOut], int]:
    conditions = _context_conditions(db, f) + _refinement_conditions(f)
    total = db.scalar(select(func.count()).select_from(Product).where(and_(*conditions))) or 0
    stmt = _apply_sort(select(Product.id).where(and_(*conditions)), f)
    stmt = stmt.limit(f.page_size).offset((f.page - 1) * f.page_size)
    ids = list(db.scalars(stmt).all())
    return cards(db, _load_products(db, ids)), total


def facets(db: Session, f: ProductFilters) -> FacetsOut:
    """Filter options with counts for the current browsing context (query/category/collection)."""
    context = and_(*_context_conditions(db, f))

    def grouped(column: Any) -> dict[str, int]:
        rows = db.execute(
            select(column, func.count()).select_from(Product).where(context).group_by(column)
        ).all()
        return {str(value): count for value, count in rows if value is not None}

    total = db.scalar(select(func.count()).select_from(Product).where(context)) or 0
    purity_counts = grouped(Product.purity)
    colour_counts = grouped(Product.metal_colour)
    category_rows = db.execute(
        select(Category.slug, Category.name, func.count(Product.id))
        .join(Product, Product.category_id == Category.id)
        .where(context)
        .group_by(Category.slug, Category.name, Category.sort_order)
        .order_by(Category.sort_order, Category.name)
    ).all()
    attr_rows = db.execute(
        select(ProductAttribute.key, ProductAttribute.value, func.count(Product.id.distinct()))
        .join(Product, Product.id == ProductAttribute.product_id)
        .where(context)
        .group_by(ProductAttribute.key, ProductAttribute.value)
        .order_by(ProductAttribute.key, ProductAttribute.value)
    ).all()
    attributes: dict[str, list[FacetValueOut]] = {}
    for key, value, count in attr_rows:
        attributes.setdefault(key, []).append(
            FacetValueOut(value=value, label=value.replace("-", " ").capitalize(), count=count)
        )
    price_min, price_max = db.execute(
        select(func.min(Product.price_from), func.max(Product.price_from)).where(context)
    ).one()
    in_stock = (
        db.scalar(select(func.count()).select_from(Product).where(context, _in_stock_condition()))
        or 0
    )
    return FacetsOut(
        total=total,
        categories=[FacetValueOut(value=s, label=n, count=c) for s, n, c in category_rows],
        purities=[
            FacetValueOut(value=p, label=PURITY_LABELS[p], count=purity_counts[p])
            for p in PURITY_LABELS
            if p in purity_counts
        ],
        metal_colours=[
            FacetValueOut(value=m, label=METAL_LABELS[m], count=colour_counts[m])
            for m in METAL_LABELS
            if m in colour_counts
        ],
        attributes=attributes,
        price_min=price_min,
        price_max=price_max,
        in_stock_count=in_stock,
    )


def get_product_detail(db: Session, slug: str) -> ProductDetailOut:
    product_id = db.scalar(
        select(Product.id).where(Product.slug == slug, Product.status == "active")
    )
    if product_id is None:
        raise NotFound("We couldn't find that piece. It may no longer be available.")
    product = _load_products(db, [product_id])[0]
    return product_detail(db, product)


def product_detail(db: Session, product: Product) -> ProductDetailOut:
    """Detail payload for an already-loaded product (also used by the admin preview)."""
    ctx = load_pricing_context(db, [product])
    variants = _active_variants(product)
    levels = inventory.levels_for(db, [v.id for v in variants])
    variant_out = []
    for v in variants:
        level = levels.get(v.id)
        price, _unit = price_out(ctx, product, v, with_breakdown=True)
        variant_out.append(
            VariantOut(
                id=str(v.id),
                sku=v.sku,
                label=v.label,
                size=v.size,
                gross_weight_g=v.gross_weight_g,
                net_gold_weight_g=v.net_gold_weight_g,
                stone_weight_ct=v.stone_weight_ct,
                is_default=v.is_default,
                stock_status=inventory.stock_status(level),
                available_quantity=max(0, min(level.available if level else 0, PURCHASE_LIMIT)),
                price=price,
            )
        )
    collections = db.execute(
        select(Collection.slug, Collection.name)
        .join(CollectionProduct, CollectionProduct.collection_id == Collection.id)
        .where(CollectionProduct.product_id == product.id, Collection.is_active)
        .order_by(Collection.sort_order)
    ).all()
    parent = product.category.parent
    return ProductDetailOut(
        id=str(product.id),
        slug=product.slug,
        name=product.name,
        description=product.description,
        category=CategoryRef(slug=product.category.slug, name=product.category.name),
        parent_category=CategoryRef(slug=parent.slug, name=parent.name) if parent else None,
        collections=[CollectionRef(slug=s, name=n) for s, n in collections],
        purity=product.purity,
        metal_colour=product.metal_colour,
        pricing_model=product.pricing_model,
        stone_details=product.stone_details,
        hallmark_details=product.hallmark_details,
        certification_details=product.certification_details,
        care_instructions=product.care_instructions,
        return_eligible=product.return_eligible,
        exchange_eligible=product.exchange_eligible,
        return_window_days=product.return_window_days,
        images=[image_out(i) for i in product.images],
        variants=variant_out,
        attributes=[AttributeOut(key=a.key, value=a.value) for a in product.attributes],
        is_sample=product.is_sample,
        seo_title=product.seo_title,
        seo_description=product.seo_description,
        published_at=product.published_at,
    )


def related_products(db: Session, slug: str, limit: int = 8) -> list[ProductCardOut]:
    product = db.scalar(select(Product).where(Product.slug == slug, Product.status == "active"))
    if product is None:
        raise NotFound()
    ids = db.scalars(
        select(Product.id)
        .where(
            Product.status == "active",
            Product.category_id == product.category_id,
            Product.id != product.id,
        )
        .order_by(Product.is_featured.desc(), Product.published_at.desc().nulls_last())
        .limit(limit)
    ).all()
    return cards(db, _load_products(db, list(ids)))


def category_out(category: Category) -> CategoryOut:
    return CategoryOut(
        slug=category.slug,
        name=category.name,
        description=category.description,
        image_url=category.image_url,
        parent_slug=category.parent.slug if category.parent else None,
        seo_title=category.seo_title,
        seo_description=category.seo_description,
    )


def collection_out(collection: Collection) -> CollectionOut:
    return CollectionOut(
        slug=collection.slug,
        name=collection.name,
        description=collection.description,
        hero_image_url=collection.hero_image_url,
        is_featured=collection.is_featured,
        seo_title=collection.seo_title,
        seo_description=collection.seo_description,
    )


def list_categories(db: Session) -> list[CategoryOut]:
    rows = db.scalars(
        select(Category)
        .where(Category.is_active)
        .options(selectinload(Category.parent))
        .order_by(Category.sort_order, Category.name)
    ).all()
    return [category_out(c) for c in rows]


def get_category(db: Session, slug: str) -> CategoryOut:
    category = db.scalar(
        select(Category)
        .where(Category.slug == slug, Category.is_active)
        .options(selectinload(Category.parent))
    )
    if category is None:
        raise NotFound("We couldn't find that category.")
    return category_out(category)


def list_collections(db: Session) -> list[CollectionOut]:
    rows = db.scalars(
        select(Collection).where(Collection.is_active).order_by(Collection.sort_order)
    ).all()
    return [collection_out(c) for c in rows]


def get_collection(db: Session, slug: str) -> CollectionOut:
    collection = db.scalar(select(Collection).where(Collection.slug == slug, Collection.is_active))
    if collection is None:
        raise NotFound("We couldn't find that collection.")
    return collection_out(collection)


def _ids(db: Session, *conditions: ColumnElement[bool], order: Any, limit: int) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(Product.id)
            .where(Product.status == "active", *conditions)
            .order_by(*order)
            .limit(limit)
        ).all()
    )


def home(db: Session) -> HomeOut:
    newest = (Product.published_at.desc().nulls_last(), Product.id)
    new_ids = _ids(db, literal(True), order=newest, limit=8)
    featured_ids = _ids(db, Product.is_featured.is_(True), order=newest, limit=8)
    best_ids = _ids(db, Product.is_bestseller.is_(True), order=newest, limit=8)
    products = {p.id: p for p in _load_products(db, list({*new_ids, *featured_ids, *best_ids}))}
    all_cards = {c.id: c for c in cards(db, list(products.values()))}

    def pick(ids: list[uuid.UUID]) -> list[ProductCardOut]:
        return [all_cards[str(i)] for i in ids if str(i) in all_cards]

    top_categories = db.scalars(
        select(Category)
        .where(Category.is_active, Category.parent_id.is_(None))
        .options(selectinload(Category.parent))
        .order_by(Category.sort_order, Category.name)
    ).all()
    featured_collections = db.scalars(
        select(Collection)
        .where(Collection.is_active, Collection.is_featured)
        .order_by(Collection.sort_order)
    ).all()
    return HomeOut(
        categories=[category_out(c) for c in top_categories],
        collections=[collection_out(c) for c in featured_collections],
        new_arrivals=pick(new_ids),
        featured=pick(featured_ids),
        bestsellers=pick(best_ids),
    )


def suggest(db: Session, raw_q: str) -> SuggestOut:
    q = normalise_query(raw_q)
    if not q or len(q) < 2:
        return SuggestOut(products=[], categories=[])
    ids = list(
        db.scalars(
            _apply_sort(
                select(Product.id).where(Product.status == "active", _search_condition(q)),
                ProductFilters(q=q),
            ).limit(6)
        ).all()
    )
    product_cards = cards(db, _load_products(db, ids))
    categories = db.scalars(
        select(Category)
        .where(Category.is_active, Category.name.ilike(_like_pattern(q), escape="\\"))
        .order_by(Category.sort_order)
        .limit(3)
    ).all()
    return SuggestOut(
        products=[
            SuggestionProductOut(slug=c.slug, name=c.name, image=c.image, price=c.price)
            for c in product_cards
        ],
        categories=[CategoryRef(slug=c.slug, name=c.name) for c in categories],
    )


def page_count(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size))


# --------------------------------------------------------------------------------------------
# Listing price cache (PRICING_ENGINE.md §8)
# --------------------------------------------------------------------------------------------


def refresh_price_cache(db: Session, product_ids: Sequence[uuid.UUID] | None = None) -> int:
    """Recompute products.price_from. Caller commits. Returns the number of products updated."""
    stmt = (
        select(Product).where(Product.status != "archived").options(selectinload(Product.variants))
    )
    if product_ids is not None:
        stmt = stmt.where(Product.id.in_(product_ids))
    products = list(db.scalars(stmt).all())
    if not products:
        return 0
    ctx = load_pricing_context(db, products)
    now = utcnow()
    for product in products:
        totals = []
        for variant in _active_variants(product):
            try:
                totals.append(ctx.price(product, variant).total)
            except PriceUnavailable:
                continue
        product.price_from = min(totals) if totals else None
        product.price_computed_at = now
    return len(products)
