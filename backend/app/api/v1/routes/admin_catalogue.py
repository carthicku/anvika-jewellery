"""Admin catalogue: products, variants, photos, categories, collections and price preview.
All routes require `catalogue:write`; every change is audited."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_request_meta, require_permission
from app.core.db import get_db
from app.core.errors import NotFound, ValidationFailed
from app.models import Category, Collection, InventoryLevel, Product, ProductVariant, User
from app.schemas.admin_catalogue import (
    AdminCategoryOut,
    AdminCollectionOut,
    AdminImageOut,
    AdminProductOut,
    AdminVariantOut,
    AttributeIn,
    CategoryIn,
    CollectionIn,
    ImageOrderIn,
    ImageUpdateIn,
    PricePreviewIn,
    PricePreviewOut,
    ProductCreateIn,
    ProductIn,
    ProductRowOut,
    VariantCreateIn,
    VariantIn,
    VariantPriceOut,
)
from app.schemas.catalogue import PriceRowOut
from app.schemas.common import OkOut, Page
from app.services import admin_catalogue as service
from app.services import audit
from app.services.auth import RequestMeta
from app.services.catalogue import image_out, page_count
from app.services.images import MAX_BYTES
from app.services.storage import Storage

router = APIRouter(prefix="/admin", tags=["admin-catalogue"])

PageNo = Annotated[int, Query(ge=1, le=10_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]


def get_storage(request: Request) -> Storage:
    storage: Storage = request.app.state.storage
    return storage


# --------------------------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------------------------


def _product_out(db: Session, product: Product) -> AdminProductOut:
    prices = service.variant_prices(db, product)
    levels = service.stock_levels(db, product)
    return AdminProductOut(
        id=str(product.id),
        name=product.name,
        slug=product.slug,
        category_id=str(product.category_id),
        status=product.status,
        metal_colour=product.metal_colour,
        purity=product.purity,
        pricing_model=product.pricing_model,
        making_charge_type=product.making_charge_type,
        making_charge_value=product.making_charge_value,
        wastage_percent=product.wastage_percent,
        description=product.description,
        stone_details=product.stone_details,
        hallmark_details=product.hallmark_details,
        certification_details=product.certification_details,
        care_instructions=product.care_instructions,
        return_eligible=product.return_eligible,
        exchange_eligible=product.exchange_eligible,
        return_window_days=product.return_window_days,
        is_featured=product.is_featured,
        is_bestseller=product.is_bestseller,
        is_sample=product.is_sample,
        seo_title=product.seo_title,
        seo_description=product.seo_description,
        attributes=[AttributeIn(key=a.key, value=a.value) for a in product.attributes],
        collection_ids=service.product_collection_ids(db, product),
        variants=[
            AdminVariantOut(
                id=str(v.id),
                sku=v.sku,
                label=v.label,
                size=v.size,
                gross_weight_g=v.gross_weight_g,
                net_gold_weight_g=v.net_gold_weight_g,
                stone_weight_ct=v.stone_weight_ct,
                stone_value=v.stone_value,
                other_charges=v.other_charges,
                other_charges_label=v.other_charges_label,
                fixed_price=v.fixed_price,
                huid=v.huid,
                is_default=v.is_default,
                is_active=v.is_active,
                sort_order=v.sort_order,
                on_hand=levels[v.id].on_hand if v.id in levels else 0,
                reserved=levels[v.id].reserved if v.id in levels else 0,
                unit_price=prices[v.id][0],
                price_error=prices[v.id][1],
            )
            for v in product.variants
        ],
        images=[
            AdminImageOut(
                id=str(i.id),
                url=i.url,
                alt_text=i.alt_text,
                width=i.width,
                height=i.height,
                renditions=i.renditions or {},
                sort_order=i.sort_order,
                is_placeholder=i.is_placeholder,
            )
            for i in sorted(product.images, key=lambda x: x.sort_order)
        ],
        publish_problems=service.publish_problems(db, product),
        published_at=product.published_at,
        updated_at=product.updated_at,
    )


@router.get(
    "/products",
    response_model=Page[ProductRowOut],
    dependencies=[Depends(require_permission("catalogue:write"))],
)
def list_products(
    response: Response,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status: Annotated[str | None, Query(max_length=16)] = None,
    category_id: uuid.UUID | None = None,
    page: PageNo = 1,
    page_size: PageSize = 25,
    db: Session = Depends(get_db),
) -> Page[ProductRowOut]:
    response.headers["Cache-Control"] = "no-store"
    stmt = select(Product)
    if q:
        like = f"%{q.strip().replace('%', '').replace('_', '')}%"
        sku_match = select(ProductVariant.product_id).where(ProductVariant.sku.ilike(like))
        stmt = stmt.where(or_(Product.name.ilike(like), Product.id.in_(sku_match)))
    if status:
        stmt = stmt.where(Product.status == status)
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    products = db.scalars(
        stmt.order_by(Product.updated_at.desc(), Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(
            selectinload(Product.variants),
            selectinload(Product.images),
            selectinload(Product.category),
        )
    ).all()
    variant_ids = [v.id for p in products for v in p.variants]
    available: dict[uuid.UUID, int] = {}
    if variant_ids:
        available = {
            row.variant_id: row.on_hand - row.reserved
            for row in db.scalars(
                select(InventoryLevel).where(InventoryLevel.variant_id.in_(variant_ids))
            ).all()
        }
    return Page(
        items=[
            ProductRowOut(
                id=str(p.id),
                name=p.name,
                slug=p.slug,
                status=p.status,
                category=p.category.name,
                purity=p.purity,
                pricing_model=p.pricing_model,
                variant_count=len(p.variants),
                available=sum(available.get(v.id, 0) for v in p.variants if v.is_active),
                price_from=p.price_from,
                image=image_out(p.images[0]) if p.images else None,
                is_sample=p.is_sample,
                updated_at=p.updated_at,
            )
            for p in products
        ],
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


@router.post("/products", response_model=AdminProductOut, status_code=201)
def create_product(
    data: ProductCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminProductOut:
    product = service.create_product(db, user, data, meta.ip)
    db.commit()
    return _product_out(db, service.load_product(db, product.id))


@router.get(
    "/products/{product_id}",
    response_model=AdminProductOut,
    dependencies=[Depends(require_permission("catalogue:write"))],
)
def get_product(
    product_id: uuid.UUID, response: Response, db: Session = Depends(get_db)
) -> AdminProductOut:
    response.headers["Cache-Control"] = "no-store"
    return _product_out(db, service.load_product(db, product_id))


@router.put("/products/{product_id}", response_model=AdminProductOut)
def update_product(
    product_id: uuid.UUID,
    data: ProductIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminProductOut:
    product = service.load_product(db, product_id, lock=True)
    service.update_product(db, user, product, data, meta.ip)
    db.commit()
    return _product_out(db, service.load_product(db, product_id))


@router.post("/products/{product_id}/variants", response_model=AdminProductOut, status_code=201)
def add_variant(
    product_id: uuid.UUID,
    data: VariantCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminProductOut:
    product = service.load_product(db, product_id, lock=True)
    service.add_variant(db, user, product, data, meta.ip)
    db.commit()
    return _product_out(db, service.load_product(db, product_id))


@router.put("/products/{product_id}/variants/{variant_id}", response_model=AdminProductOut)
def update_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    data: VariantIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminProductOut:
    product = service.load_product(db, product_id, lock=True)
    service.update_variant(db, user, product, variant_id, data, meta.ip)
    db.commit()
    return _product_out(db, service.load_product(db, product_id))


@router.post("/products/{product_id}/images", response_model=AdminProductOut, status_code=201)
async def upload_image(
    product_id: uuid.UUID,
    request: Request,
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP, up to 10 MB")],
    alt_text: Annotated[str, Form(max_length=200)] = "",
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminProductOut:
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValidationFailed({"file": "The image is larger than 10 MB."})

    def work() -> AdminProductOut:
        product = service.load_product(db, product_id, lock=True)
        service.add_image(db, storage, user, product, data, alt_text, meta.ip)
        db.commit()
        return _product_out(db, service.load_product(db, product_id))

    return await run_in_threadpool(work)


@router.patch("/products/{product_id}/images/{image_id}", response_model=AdminProductOut)
def update_image(
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    data: ImageUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminProductOut:
    product = service.load_product(db, product_id, lock=True)
    image = service.update_image(product, image_id, data.alt_text)
    audit.record(
        db,
        actor=user,
        action="image.update",
        entity_type="product",
        entity_id=product.id,
        changes={"image_id": str(image.id), "alt_text": image.alt_text},
        ip_address=meta.ip,
    )
    db.commit()
    return _product_out(db, service.load_product(db, product_id))


@router.put("/products/{product_id}/images/order", response_model=AdminProductOut)
def reorder_images(
    product_id: uuid.UUID,
    data: ImageOrderIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminProductOut:
    product = service.load_product(db, product_id, lock=True)
    service.reorder_images(product, data.image_ids)
    audit.record(
        db,
        actor=user,
        action="image.reorder",
        entity_type="product",
        entity_id=product.id,
        changes={"order": [str(i) for i in data.image_ids]},
        ip_address=meta.ip,
    )
    db.commit()
    return _product_out(db, service.load_product(db, product_id))


@router.delete("/products/{product_id}/images/{image_id}", response_model=AdminProductOut)
def delete_image(
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminProductOut:
    product = service.load_product(db, product_id, lock=True)
    service.delete_image(db, storage, user, product, image_id, meta.ip)
    db.commit()
    return _product_out(db, service.load_product(db, product_id))


@router.post(
    "/catalogue/price-preview",
    response_model=PricePreviewOut,
    dependencies=[Depends(require_permission("catalogue:write"))],
)
def price_preview(data: PricePreviewIn, db: Session = Depends(get_db)) -> PricePreviewOut:
    """What customers would pay with these inputs and today's rate and tax. Nothing is saved."""
    rate, rows = service.preview_prices(db, data)
    return PricePreviewOut(
        gold_rate_per_gram=rate if data.pricing_model == "weight_based" else None,
        variants=[
            VariantPriceOut(
                label=label,
                total=total,
                breakdown=[PriceRowOut(**row) for row in breakdown],
                error=error,
            )
            for label, total, breakdown, error in rows
        ],
        note="Includes GST at the configured rates; automatic discounts and coupons are not "
        "included here.",
    )


# --------------------------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------------------------


def _category_out(db: Session, c: Category) -> AdminCategoryOut:
    count = db.scalar(select(func.count()).select_from(Product).where(Product.category_id == c.id))
    return AdminCategoryOut(
        id=str(c.id),
        name=c.name,
        slug=c.slug,
        parent_id=str(c.parent_id) if c.parent_id else None,
        description=c.description,
        sort_order=c.sort_order,
        is_active=c.is_active,
        seo_title=c.seo_title,
        seo_description=c.seo_description,
        product_count=count or 0,
    )


@router.get(
    "/categories",
    response_model=list[AdminCategoryOut],
    dependencies=[Depends(require_permission("catalogue:write"))],
)
def list_categories(db: Session = Depends(get_db)) -> list[AdminCategoryOut]:
    rows = db.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()
    return [_category_out(db, c) for c in rows]


@router.post("/categories", response_model=AdminCategoryOut, status_code=201)
def create_category(
    data: CategoryIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminCategoryOut:
    category = service.save_category(db, user, data, None, meta.ip)
    db.commit()
    return _category_out(db, category)


def _category(db: Session, category_id: uuid.UUID) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFound("Category not found.")
    return category


@router.put("/categories/{category_id}", response_model=AdminCategoryOut)
def update_category(
    category_id: uuid.UUID,
    data: CategoryIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminCategoryOut:
    category = service.save_category(db, user, data, _category(db, category_id), meta.ip)
    db.commit()
    return _category_out(db, category)


@router.delete("/categories/{category_id}", response_model=OkOut)
def delete_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> OkOut:
    service.delete_category(db, user, _category(db, category_id), meta.ip)
    db.commit()
    return OkOut(message="Category deleted.")


# --------------------------------------------------------------------------------------------
# Collections
# --------------------------------------------------------------------------------------------


def _collection_out(db: Session, c: Collection) -> AdminCollectionOut:
    return AdminCollectionOut(
        id=str(c.id),
        name=c.name,
        slug=c.slug,
        description=c.description,
        is_active=c.is_active,
        is_featured=c.is_featured,
        sort_order=c.sort_order,
        seo_title=c.seo_title,
        seo_description=c.seo_description,
        product_ids=service.collection_product_ids(db, c),
    )


@router.get(
    "/collections",
    response_model=list[AdminCollectionOut],
    dependencies=[Depends(require_permission("catalogue:write"))],
)
def list_collections(db: Session = Depends(get_db)) -> list[AdminCollectionOut]:
    rows = db.scalars(select(Collection).order_by(Collection.sort_order, Collection.name)).all()
    return [_collection_out(db, c) for c in rows]


@router.post("/collections", response_model=AdminCollectionOut, status_code=201)
def create_collection(
    data: CollectionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminCollectionOut:
    collection = service.save_collection(db, user, data, None, meta.ip)
    db.commit()
    return _collection_out(db, collection)


@router.put("/collections/{collection_id}", response_model=AdminCollectionOut)
def update_collection(
    collection_id: uuid.UUID,
    data: CollectionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalogue:write")),
    meta: RequestMeta = Depends(get_request_meta),
) -> AdminCollectionOut:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise NotFound("Collection not found.")
    service.save_collection(db, user, data, collection, meta.ip)
    db.commit()
    return _collection_out(db, collection)
