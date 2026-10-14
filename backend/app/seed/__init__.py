"""Deterministic development seed (docs/development/SEED_DATA.md).

Idempotent: rows are matched by natural keys (slug, SKU, code) and updated instead of duplicated.
Stock is only set when a variant is first created, so re-seeding never overwrites real stock moves.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import (
    Category,
    Collection,
    CollectionProduct,
    ContentPage,
    Coupon,
    Discount,
    GoldRate,
    Product,
    ProductAttribute,
    ProductImage,
    ProductVariant,
    ShippingMethod,
)
from app.seed import catalogue_data as data
from app.seed.content_data import PAGES
from app.services import inventory, store_settings
from app.services.catalogue import refresh_price_cache

PLACEHOLDER_PATH = "/images/placeholders"


def _image(name: str) -> str:
    return f"{PLACEHOLDER_PATH}/{name}.svg"


def seed_categories(db: Session) -> dict[str, Category]:
    result = {}
    for order, (slug, name, description, illustration) in enumerate(data.CATEGORIES):
        category = db.scalar(select(Category).where(Category.slug == slug)) or Category(slug=slug)
        category.name = name
        category.description = description
        category.image_url = _image(illustration)
        category.sort_order = order
        category.is_active = True
        db.add(category)
        result[slug] = category
    db.flush()
    return result


def seed_collections(db: Session) -> dict[str, Collection]:
    result = {}
    for order, (slug, name, description, featured, illustration) in enumerate(data.COLLECTIONS):
        collection = db.scalar(select(Collection).where(Collection.slug == slug)) or Collection(
            slug=slug
        )
        collection.name = name
        collection.description = description
        collection.is_featured = featured
        collection.hero_image_url = _image(illustration)
        collection.sort_order = order
        collection.is_active = True
        db.add(collection)
        result[slug] = collection
    db.flush()
    return result


def seed_products(
    db: Session, categories: dict[str, Category], collections: dict[str, Collection]
) -> int:
    now = utcnow()
    for spec in data.PRODUCTS:
        product = db.scalar(select(Product).where(Product.slug == spec.slug))
        if product is None:
            product = Product(slug=spec.slug)
            db.add(product)
        product.name = spec.name
        product.category_id = categories[spec.category].id
        product.status = "active"
        product.metal_colour = spec.colour
        product.purity = spec.purity
        product.pricing_model = spec.model
        product.making_charge_type, product.making_charge_value = spec.making
        product.wastage_percent = spec.wastage
        product.description = spec.description
        product.stone_details = spec.stone_details
        product.care_instructions = spec.care
        product.return_eligible, product.exchange_eligible, product.return_window_days = (
            spec.returns
        )
        product.is_featured = spec.featured
        product.is_bestseller = spec.bestseller
        product.is_sample = True
        product.published_at = now - timedelta(days=spec.published_days_ago)
        product.seo_description = f"{spec.name} in {spec.purity} gold. {spec.description}"
        db.flush()

        existing = {v.sku: v for v in product.variants}
        for order, vs in enumerate(spec.variants):
            variant = existing.get(vs.sku)
            created = variant is None
            if variant is None:
                variant = ProductVariant(product_id=product.id, sku=vs.sku)
                db.add(variant)
            variant.label = vs.label
            variant.size = vs.size
            variant.gross_weight_g = vs.gross
            variant.net_gold_weight_g = vs.net
            variant.stone_weight_ct = vs.stone_ct
            variant.stone_value = vs.stone_value
            variant.other_charges = vs.other
            variant.other_charges_label = vs.other_label
            variant.fixed_price = vs.fixed
            variant.is_default = vs.default
            variant.is_active = True
            variant.sort_order = order
            db.flush()
            if created:
                inventory.set_initial_stock(db, variant.id, vs.stock, note="Seed: sample stock")

        db.query(ProductImage).filter(ProductImage.product_id == product.id).delete()
        for order, suffix in enumerate(("", "-detail")):
            db.add(
                ProductImage(
                    product_id=product.id,
                    url=_image(spec.illustration + suffix),
                    alt_text=f"{spec.name} — sample illustration" + (" (detail)" if suffix else ""),
                    width=800,
                    height=1000,
                    sort_order=order,
                    is_placeholder=True,
                )
            )

        db.query(ProductAttribute).filter(ProductAttribute.product_id == product.id).delete()
        for key, value in spec.attrs.items():
            db.add(ProductAttribute(product_id=product.id, key=key, value=value))

        db.query(CollectionProduct).filter(CollectionProduct.product_id == product.id).delete()
        for order, slug in enumerate(spec.collections):
            db.add(
                CollectionProduct(
                    collection_id=collections[slug].id, product_id=product.id, sort_order=order
                )
            )
    db.flush()
    return len(data.PRODUCTS)


def seed_gold_rates(db: Session) -> None:
    """Add illustrative rates only for purities that have none yet (never overrides real rates)."""
    effective = utcnow() - timedelta(minutes=5)
    for purity, rate in data.GOLD_RATES.items():
        has_rate = db.scalar(select(GoldRate.id).where(GoldRate.purity == purity).limit(1))
        if not has_rate:
            db.add(
                GoldRate(
                    purity=purity,
                    rate_per_gram=rate,
                    effective_from=effective,
                    source_note=data.RATE_SOURCE_NOTE,
                )
            )
    db.flush()


def seed_shipping(db: Session) -> None:
    for (
        code,
        name,
        description,
        fee,
        free_above,
        min_days,
        max_days,
        order,
    ) in data.SHIPPING_METHODS:
        method = db.scalar(select(ShippingMethod).where(ShippingMethod.code == code))
        if method is None:
            method = ShippingMethod(code=code)
            db.add(method)
        method.name = name
        method.description = description
        method.fee = fee
        method.free_above = free_above
        method.min_days = min_days
        method.max_days = max_days
        method.sort_order = order
        method.is_active = True
    db.flush()


def seed_discount(db: Session, collections: dict[str, Collection]) -> None:
    spec = data.SAMPLE_DISCOUNT
    name = str(spec["name"])
    discount = db.scalar(select(Discount).where(Discount.name == name))
    if discount is None:
        discount = Discount(name=name, starts_at=utcnow() - timedelta(days=1))
        db.add(discount)
    discount.kind = str(spec["kind"])
    discount.value = Decimal(str(spec["value"]))
    discount.scope = str(spec["scope"])
    discount.scope_id = collections[str(spec["collection_slug"])].id
    discount.is_active = True
    db.flush()


def seed_coupons(db: Session) -> None:
    now = utcnow()
    for spec in data.SAMPLE_COUPONS:
        coupon = db.scalar(select(Coupon).where(Coupon.code == spec["code"]))
        if coupon is None:
            coupon = Coupon(code=spec["code"])
            db.add(coupon)
        coupon.description = spec["description"]
        coupon.kind = spec["kind"]
        coupon.value = spec["value"]
        coupon.max_discount_amount = spec["max_discount_amount"]
        coupon.min_order_amount = spec["min_order_amount"]
        coupon.usage_limit_per_customer = spec["usage_limit_per_customer"]
        coupon.starts_at = now - timedelta(days=30)
        coupon.ends_at = now - timedelta(days=1) if spec["expired"] else None
        coupon.is_active = True
        coupon.is_sample = True
    db.flush()


def seed_content(db: Session) -> None:
    for page_data in PAGES:
        slug = str(page_data["slug"])
        page = db.scalar(select(ContentPage).where(ContentPage.slug == slug))
        if page is not None and not page.is_draft_template:
            continue  # the owner has edited and approved this page — never overwrite it
        if page is None:
            page = ContentPage(slug=slug)
            db.add(page)
        page.title = str(page_data["title"])
        page.summary = str(page_data["summary"])
        page.body_markdown = str(page_data["body"])
        page.is_draft_template = True
    db.flush()


def seed_settings(db: Session) -> None:
    store_settings.set_group(
        db,
        "announcement",
        {"enabled": True, "text": "Free standard delivery on orders above ₹25,000", "link": None},
    )
    db.flush()


def run_seed(db: Session) -> dict[str, int]:
    categories = seed_categories(db)
    collections = seed_collections(db)
    products = seed_products(db, categories, collections)
    seed_gold_rates(db)
    seed_shipping(db)
    seed_discount(db, collections)
    seed_coupons(db)
    seed_content(db)
    seed_settings(db)
    db.flush()
    priced = refresh_price_cache(db)
    return {
        "categories": len(categories),
        "collections": len(collections),
        "products": products,
        "prices_cached": priced,
        "content_pages": len(PAGES),
    }
