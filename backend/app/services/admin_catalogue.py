"""Catalogue administration: products, variants, images, categories and collections.

Rules:
* Products are never hard-deleted (orders keep their own snapshots); they are archived.
* A product can only be published (status `active`) when every active variant can be priced —
  weight-based pieces need a net gold weight and a gold rate for their purity, fixed-price pieces
  need a pre-tax price.
* Every change is audited and refreshes the listing price cache.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import Conflict, NotFound, ValidationFailed
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
    User,
)
from app.schemas.admin_catalogue import (
    CategoryIn,
    CollectionIn,
    PricePreviewIn,
    ProductCreateIn,
    ProductIn,
    VariantCreateIn,
    VariantIn,
)
from app.services import audit, images, inventory
from app.services.catalogue import refresh_price_cache
from app.services.pricing import (
    GoldRateInput,
    PriceUnavailable,
    ProductPricing,
    VariantPricing,
    price_unit,
    unit_breakdown,
)
from app.services.pricing_context import load_pricing_context
from app.services.storage import Storage

PRODUCT_FIELDS = (
    "name",
    "category_id",
    "status",
    "metal_colour",
    "purity",
    "pricing_model",
    "making_charge_type",
    "making_charge_value",
    "wastage_percent",
    "description",
    "stone_details",
    "hallmark_details",
    "certification_details",
    "care_instructions",
    "return_eligible",
    "exchange_eligible",
    "return_window_days",
    "is_featured",
    "is_bestseller",
    "seo_title",
    "seo_description",
)
VARIANT_FIELDS = (
    "sku",
    "label",
    "size",
    "gross_weight_g",
    "net_gold_weight_g",
    "stone_weight_ct",
    "stone_value",
    "other_charges",
    "other_charges_label",
    "fixed_price",
    "huid",
    "is_default",
    "is_active",
    "sort_order",
)


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:90] or "item"


def _unique_slug(db: Session, model: type, wanted: str, exclude: uuid.UUID | None = None) -> str:
    def taken(slug: str) -> bool:
        stmt = select(model.id).where(model.slug == slug)  # type: ignore[attr-defined]
        if exclude is not None:
            stmt = stmt.where(model.id != exclude)  # type: ignore[attr-defined]
        return db.scalar(stmt) is not None

    if not taken(wanted):
        return wanted
    for n in range(2, 1000):
        candidate = f"{wanted}-{n}"
        if not taken(candidate):
            return candidate
    raise Conflict("Couldn't find a free web address for this name.")


def _explicit_slug(db: Session, model: type, slug: str, exclude: uuid.UUID | None) -> str:
    stmt = select(model.id).where(model.slug == slug)  # type: ignore[attr-defined]
    if exclude is not None:
        stmt = stmt.where(model.id != exclude)  # type: ignore[attr-defined]
    if db.scalar(stmt) is not None:
        raise ValidationFailed({"slug": "This web address is already used."})
    return slug


# --------------------------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------------------------


def load_product(db: Session, product_id: uuid.UUID, *, lock: bool = False) -> Product:
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.variants),
            selectinload(Product.images),
            selectinload(Product.attributes),
        )
        .execution_options(populate_existing=True)
    )
    if lock:
        stmt = stmt.with_for_update(of=Product)
    product = db.scalar(stmt)
    if product is None:
        raise NotFound("Product not found.")
    return product


def publish_problems(db: Session, product: Product) -> list[str]:
    """Why this product can't be shown to customers yet (empty list = ready)."""
    problems: list[str] = []
    active = [v for v in product.variants if v.is_active]
    if not active:
        problems.append("Add at least one active variant.")
    ctx = load_pricing_context(db, [product])
    for variant in active:
        try:
            ctx.price(product, variant)
        except PriceUnavailable as exc:
            problems.append(f"{variant.sku} {price_problem(exc)}.")
    return problems


def _check_category(db: Session, category_id: uuid.UUID) -> None:
    if db.get(Category, category_id) is None:
        raise ValidationFailed({"category_id": "Choose an existing category."})


def _check_variant_inputs(
    pricing_model: str, variants: Sequence[VariantIn | ProductVariant]
) -> None:
    """Each active variant needs the input its pricing model uses."""
    errors: dict[str, str] = {}
    for i, v in enumerate(variants):
        if not v.is_active:
            continue
        if pricing_model == "weight_based" and v.net_gold_weight_g is None:
            errors[f"variants.{i}.net_gold_weight_g"] = (
                f"{v.sku}: weight-based pricing needs the net gold weight."
            )
        if pricing_model == "fixed" and v.fixed_price is None:
            errors[f"variants.{i}.fixed_price"] = f"{v.sku}: fixed pricing needs a pre-tax price."
    if errors:
        raise ValidationFailed(errors)


def _set_relations(db: Session, product: Product, data: ProductIn) -> None:
    # Keep matching rows, remove the rest, then add new ones (avoids unique-key clashes).
    wanted = list(dict.fromkeys((a.key, a.value) for a in data.attributes))
    for attribute in list(product.attributes):
        if (attribute.key, attribute.value) not in wanted:
            product.attributes.remove(attribute)
    db.flush()
    existing = {(a.key, a.value) for a in product.attributes}
    for key, value in wanted:
        if (key, value) not in existing:
            product.attributes.append(ProductAttribute(key=key, value=value))
    db.execute(delete(CollectionProduct).where(CollectionProduct.product_id == product.id))
    for collection_id in dict.fromkeys(data.collection_ids):
        if db.get(Collection, collection_id) is None:
            raise ValidationFailed({"collection_ids": "Choose existing collections."})
        db.add(CollectionProduct(collection_id=collection_id, product_id=product.id))


def _sku_free(db: Session, sku: str, exclude: uuid.UUID | None = None) -> None:
    stmt = select(ProductVariant.id).where(ProductVariant.sku == sku)
    if exclude is not None:
        stmt = stmt.where(ProductVariant.id != exclude)
    if db.scalar(stmt) is not None:
        raise ValidationFailed({"sku": f"SKU {sku} is already used."})


def _publish_guard(db: Session, product: Product) -> None:
    if product.status != "active":
        return
    problems = publish_problems(db, product)
    if problems:
        raise ValidationFailed(
            {"status": "This product can't be published yet: " + " ".join(problems)}
        )
    if product.published_at is None:
        product.published_at = utcnow()


def create_product(db: Session, actor: User, data: ProductCreateIn, ip: str | None) -> Product:
    _check_category(db, data.category_id)
    _check_variant_inputs(data.pricing_model, list(data.variants))
    skus = [v.sku for v in data.variants]
    if len(set(skus)) != len(skus):
        raise ValidationFailed({"variants": "Each variant needs its own SKU."})
    for sku in skus:
        _sku_free(db, sku)
    slug = (
        _explicit_slug(db, Product, data.slug, None)
        if data.slug
        else _unique_slug(db, Product, slugify(data.name))
    )
    product = Product(slug=slug, **{f: getattr(data, f) for f in PRODUCT_FIELDS})
    db.add(product)
    db.flush()
    for i, v in enumerate(data.variants):
        variant = ProductVariant(
            product_id=product.id,
            **{f: getattr(v, f) for f in VARIANT_FIELDS},
        )
        variant.is_default = v.is_default or (
            i == 0 and not any(x.is_default for x in data.variants)
        )
        db.add(variant)
        db.flush()
        inventory.set_initial_stock(db, variant.id, v.initial_stock, actor_user_id=actor.id)
    _set_relations(db, product, data)
    db.flush()
    db.refresh(product)
    product = load_product(db, product.id)
    _publish_guard(db, product)
    audit.record(
        db,
        actor=actor,
        action="product.create",
        entity_type="product",
        entity_id=product.id,
        changes={"name": product.name, "status": product.status, "skus": skus},
        ip_address=ip,
    )
    refresh_price_cache(db, [product.id])
    return product


def update_product(
    db: Session, actor: User, product: Product, data: ProductIn, ip: str | None
) -> Product:
    _check_category(db, data.category_id)
    _check_variant_inputs(data.pricing_model, list(product.variants))
    changes = {
        f: [str(getattr(product, f)), str(getattr(data, f))]
        for f in PRODUCT_FIELDS
        if getattr(product, f) != getattr(data, f)
    }
    if data.slug and data.slug != product.slug:
        product.slug = _explicit_slug(db, Product, data.slug, product.id)
        changes["slug"] = [product.slug, data.slug]
    for f in PRODUCT_FIELDS:
        setattr(product, f, getattr(data, f))
    _set_relations(db, product, data)
    db.flush()
    _publish_guard(db, product)
    audit.record(
        db,
        actor=actor,
        action="product.update",
        entity_type="product",
        entity_id=product.id,
        changes=changes,
        ip_address=ip,
    )
    refresh_price_cache(db, [product.id])
    return product


def add_variant(
    db: Session, actor: User, product: Product, data: VariantCreateIn, ip: str | None
) -> ProductVariant:
    _sku_free(db, data.sku)
    variant = ProductVariant(product_id=product.id, **{f: getattr(data, f) for f in VARIANT_FIELDS})
    db.add(variant)
    db.flush()
    inventory.set_initial_stock(db, variant.id, data.initial_stock, actor_user_id=actor.id)
    if variant.is_default:
        _single_default(product, variant)
    db.flush()
    db.refresh(product)
    _publish_guard(db, product)
    audit.record(
        db,
        actor=actor,
        action="variant.create",
        entity_type="product",
        entity_id=product.id,
        changes={"sku": data.sku, "initial_stock": data.initial_stock},
        ip_address=ip,
    )
    refresh_price_cache(db, [product.id])
    return variant


def _single_default(product: Product, chosen: ProductVariant) -> None:
    for other in product.variants:
        if other.id != chosen.id:
            other.is_default = False


def update_variant(
    db: Session,
    actor: User,
    product: Product,
    variant_id: uuid.UUID,
    data: VariantIn,
    ip: str | None,
) -> ProductVariant:
    variant = next((v for v in product.variants if v.id == variant_id), None)
    if variant is None:
        raise NotFound("Variant not found.")
    _sku_free(db, data.sku, exclude=variant.id)
    if (
        product.pricing_model == "weight_based"
        and data.is_active
        and data.net_gold_weight_g is None
    ):
        raise ValidationFailed(
            {"net_gold_weight_g": "Weight-based pricing needs the net gold weight."}
        )
    if product.pricing_model == "fixed" and data.is_active and data.fixed_price is None:
        raise ValidationFailed({"fixed_price": "Fixed pricing needs a pre-tax price."})
    changes = {
        f: [str(getattr(variant, f)), str(getattr(data, f))]
        for f in VARIANT_FIELDS
        if getattr(variant, f) != getattr(data, f)
    }
    for f in VARIANT_FIELDS:
        setattr(variant, f, getattr(data, f))
    if variant.is_default:
        _single_default(product, variant)
    db.flush()
    _publish_guard(db, product)
    audit.record(
        db,
        actor=actor,
        action="variant.update",
        entity_type="product",
        entity_id=product.id,
        changes={"sku": variant.sku, **changes},
        ip_address=ip,
    )
    refresh_price_cache(db, [product.id])
    return variant


def variant_prices(
    db: Session, product: Product
) -> dict[uuid.UUID, tuple[Decimal | None, str | None]]:
    ctx = load_pricing_context(db, [product])
    out: dict[uuid.UUID, tuple[Decimal | None, str | None]] = {}
    for variant in product.variants:
        try:
            out[variant.id] = (ctx.price(product, variant).total, None)
        except PriceUnavailable as exc:
            out[variant.id] = (None, price_problem(exc))
    return out


def stock_levels(db: Session, product: Product) -> dict[uuid.UUID, InventoryLevel]:
    return inventory.levels_for(db, [v.id for v in product.variants])


# --------------------------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------------------------


def add_image(
    db: Session,
    storage: Storage,
    actor: User,
    product: Product,
    data: bytes,
    alt_text: str,
    ip: str | None,
) -> ProductImage:
    if len(product.images) >= 20:
        raise Conflict("A product can have up to 20 photos.", code="TOO_MANY_IMAGES")
    processed = images.process(data)
    key = images.new_image_key(str(product.id))
    urls: dict[str, str] = {}
    for width, blob in processed.renditions.items():
        urls[str(width)] = storage.save(f"{key}-{width}.webp", blob, "image/webp")
    largest = max(processed.renditions)
    image = ProductImage(
        product_id=product.id,
        url=urls[str(largest)],
        storage_key=key,
        renditions=urls,
        alt_text=(alt_text.strip() or product.name)[:200],
        width=largest,
        height=round(processed.height * largest / processed.width),
        sort_order=max((i.sort_order for i in product.images), default=-1) + 1,
        is_placeholder=False,
    )
    db.add(image)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="image.upload",
        entity_type="product",
        entity_id=product.id,
        changes={"image_id": str(image.id), "widths": sorted(processed.renditions)},
        ip_address=ip,
    )
    return image


def _image(product: Product, image_id: uuid.UUID) -> ProductImage:
    image = next((i for i in product.images if i.id == image_id), None)
    if image is None:
        raise NotFound("Photo not found.")
    return image


def update_image(product: Product, image_id: uuid.UUID, alt_text: str) -> ProductImage:
    image = _image(product, image_id)
    image.alt_text = (alt_text.strip() or product.name)[:200]
    return image


def reorder_images(product: Product, image_ids: list[uuid.UUID]) -> None:
    current = {i.id for i in product.images}
    if set(image_ids) != current or len(image_ids) != len(current):
        raise ValidationFailed({"image_ids": "List every photo of this product exactly once."})
    order = {image_id: n for n, image_id in enumerate(image_ids)}
    for image in product.images:
        image.sort_order = order[image.id]


def delete_image(
    db: Session,
    storage: Storage,
    actor: User,
    product: Product,
    image_id: uuid.UUID,
    ip: str | None,
) -> None:
    image = _image(product, image_id)
    if image.storage_key and not image.is_placeholder:
        for width in image.renditions:
            storage.delete(f"{image.storage_key}-{width}.webp")
    product.images.remove(image)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="image.delete",
        entity_type="product",
        entity_id=product.id,
        changes={"image_id": str(image_id)},
        ip_address=ip,
    )


# --------------------------------------------------------------------------------------------
# Price preview (nothing saved)
# --------------------------------------------------------------------------------------------


PreviewRow = tuple[str, Decimal | None, list[dict[str, Any]], str | None]

PRICE_PROBLEMS = {
    "MISSING_FIXED_PRICE": "needs a pre-tax price",
    "NO_GOLD_RATE": "has no gold rate for its purity yet (add one under Gold rates)",
    "PURITY_MISMATCH": "uses a gold rate for a different purity",
    "MISSING_WEIGHT": "needs a net gold weight",
}


def price_problem(exc: PriceUnavailable) -> str:
    return PRICE_PROBLEMS.get(str(exc), "can't be priced")


def preview_prices(db: Session, data: PricePreviewIn) -> tuple[Decimal | None, list[PreviewRow]]:
    ctx = load_pricing_context(db, [])
    rate = ctx.rates.get(data.purity)
    rate_input = (
        GoldRateInput(rate.id, rate.purity, rate.rate_per_gram)
        if rate and data.pricing_model == "weight_based"
        else None
    )
    pricing = ProductPricing(
        pricing_model=data.pricing_model,
        purity=data.purity,
        making_charge_type=data.making_charge_type,
        making_charge_value=data.making_charge_value,
        wastage_percent=data.wastage_percent,
    )
    rows: list[PreviewRow] = []
    for v in data.variants:
        try:
            unit = price_unit(
                pricing,
                VariantPricing(
                    net_gold_weight_g=v.net_gold_weight_g,
                    fixed_price=v.fixed_price,
                    stone_value=v.stone_value,
                    other_charges=v.other_charges,
                ),
                rate_input,
                ctx.tax,
                [],
            )
            rows.append((v.label, unit.total, unit_breakdown(unit), None))
        except PriceUnavailable as exc:
            rows.append((v.label, None, [], f"{v.label} {price_problem(exc)}."))
    return (rate.rate_per_gram if rate else None), rows


# --------------------------------------------------------------------------------------------
# Categories and collections
# --------------------------------------------------------------------------------------------


def save_category(
    db: Session, actor: User, data: CategoryIn, category: Category | None, ip: str | None
) -> Category:
    if data.parent_id is not None:
        parent = db.get(Category, data.parent_id)
        if parent is None or (category is not None and parent.id == category.id):
            raise ValidationFailed({"parent_id": "Choose a different parent category."})
        if parent.parent_id is not None:
            raise ValidationFailed({"parent_id": "Categories can only be nested one level deep."})
    if category is None:
        category = Category(
            slug=_explicit_slug(db, Category, data.slug, None)
            if data.slug
            else _unique_slug(db, Category, slugify(data.name))
        )
        db.add(category)
        action = "category.create"
    else:
        if data.slug and data.slug != category.slug:
            category.slug = _explicit_slug(db, Category, data.slug, category.id)
        action = "category.update"
    for f in (
        "name",
        "parent_id",
        "description",
        "sort_order",
        "is_active",
        "seo_title",
        "seo_description",
    ):
        setattr(category, f, getattr(data, f))
    db.flush()
    audit.record(
        db,
        actor=actor,
        action=action,
        entity_type="category",
        entity_id=category.id,
        changes=data.model_dump(mode="json"),
        ip_address=ip,
    )
    return category


def delete_category(db: Session, actor: User, category: Category, ip: str | None) -> None:
    in_use = db.scalar(
        select(func.count()).select_from(Product).where(Product.category_id == category.id)
    )
    children = db.scalar(
        select(func.count()).select_from(Category).where(Category.parent_id == category.id)
    )
    if in_use or children:
        raise Conflict(
            "This category still has products or sub-categories. Move them first, or hide the "
            "category instead.",
            code="CATEGORY_IN_USE",
        )
    db.delete(category)
    audit.record(
        db,
        actor=actor,
        action="category.delete",
        entity_type="category",
        entity_id=category.id,
        changes={"name": category.name},
        ip_address=ip,
    )


def save_collection(
    db: Session, actor: User, data: CollectionIn, collection: Collection | None, ip: str | None
) -> Collection:
    if collection is None:
        collection = Collection(
            slug=_explicit_slug(db, Collection, data.slug, None)
            if data.slug
            else _unique_slug(db, Collection, slugify(data.name))
        )
        db.add(collection)
        action = "collection.create"
    else:
        if data.slug and data.slug != collection.slug:
            collection.slug = _explicit_slug(db, Collection, data.slug, collection.id)
        action = "collection.update"
    for f in (
        "name",
        "description",
        "is_active",
        "is_featured",
        "sort_order",
        "seo_title",
        "seo_description",
    ):
        setattr(collection, f, getattr(data, f))
    db.flush()
    db.execute(delete(CollectionProduct).where(CollectionProduct.collection_id == collection.id))
    ids = list(dict.fromkeys(data.product_ids))
    existing = (
        set(db.scalars(select(Product.id).where(Product.id.in_(ids))).all()) if ids else set()
    )
    if len(existing) != len(ids):
        raise ValidationFailed({"product_ids": "Some products don't exist."})
    for n, product_id in enumerate(ids):
        db.add(CollectionProduct(collection_id=collection.id, product_id=product_id, sort_order=n))
    db.flush()
    audit.record(
        db,
        actor=actor,
        action=action,
        entity_type="collection",
        entity_id=collection.id,
        changes={**data.model_dump(mode="json", exclude={"product_ids"}), "products": len(ids)},
        ip_address=ip,
    )
    # Collection discounts depend on membership (including products just removed).
    refresh_price_cache(db)
    return collection


def collection_product_ids(db: Session, collection: Collection) -> list[str]:
    return [
        str(pid)
        for pid in db.scalars(
            select(CollectionProduct.product_id)
            .where(CollectionProduct.collection_id == collection.id)
            .order_by(CollectionProduct.sort_order)
        ).all()
    ]


def product_collection_ids(db: Session, product: Product) -> list[str]:
    return [
        str(cid)
        for cid in db.scalars(
            select(CollectionProduct.collection_id).where(
                CollectionProduct.product_id == product.id
            )
        ).all()
    ]
