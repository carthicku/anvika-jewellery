"""Public catalogue endpoints (no authentication). Only active products are exposed."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import NotFound, ValidationFailed
from app.models.enums import METAL_COLOURS, PURITIES
from app.schemas.catalogue import (
    CategoryOut,
    CollectionOut,
    FacetsOut,
    HomeOut,
    ProductCardOut,
    ProductDetailOut,
    SuggestOut,
)
from app.schemas.common import Page
from app.services import catalogue
from app.services.catalogue import ProductFilters

router = APIRouter(tags=["catalogue"])

PUBLIC_CACHE = "public, max-age=60"


def _cache(response: Response) -> None:
    response.headers["Cache-Control"] = PUBLIC_CACHE


def product_filters(
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=100)] = None,
    collection: Annotated[str | None, Query(max_length=100)] = None,
    purity: Annotated[list[str], Query()] = [],  # noqa: B006 - FastAPI query list default
    metal_colour: Annotated[list[str], Query()] = [],  # noqa: B006
    min_price: Annotated[Decimal | None, Query(ge=0, le=100_000_000)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0, le=100_000_000)] = None,
    in_stock: bool = False,
    attr: Annotated[
        list[str], Query(description="Attribute filters as key:value, e.g. occasion:wedding")
    ] = [],  # noqa: B006
    sort: Literal["relevance", "newest", "price_asc", "price_desc"] = "relevance",
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=48)] = 24,
) -> ProductFilters:
    errors: dict[str, str] = {}
    if any(p not in PURITIES for p in purity):
        errors["purity"] = f"Purity must be one of {', '.join(PURITIES)}."
    if any(m not in METAL_COLOURS for m in metal_colour):
        errors["metal_colour"] = "Unknown metal colour."
    attributes: dict[str, list[str]] = {}
    for item in attr:
        key, sep, value = item.partition(":")
        if not sep or not key or not value or len(key) > 40 or len(value) > 80:
            errors["attr"] = "Attribute filters must look like key:value."
            break
        attributes.setdefault(key, []).append(value)
    if min_price is not None and max_price is not None and min_price > max_price:
        errors["min_price"] = "Minimum price cannot be above maximum price."
    if errors:
        raise ValidationFailed(errors)
    return ProductFilters(
        q=catalogue.normalise_query(q),
        category=category,
        collection=collection,
        purity=purity,
        metal_colour=metal_colour,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        attributes=attributes,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/home", response_model=HomeOut)
def home(response: Response, db: Session = Depends(get_db)) -> HomeOut:
    _cache(response)
    return catalogue.home(db)


@router.get("/categories", response_model=list[CategoryOut])
def categories(response: Response, db: Session = Depends(get_db)) -> list[CategoryOut]:
    _cache(response)
    return catalogue.list_categories(db)


@router.get("/categories/{slug}", response_model=CategoryOut)
def category(slug: str, response: Response, db: Session = Depends(get_db)) -> CategoryOut:
    _cache(response)
    return catalogue.get_category(db, slug)


@router.get("/collections", response_model=list[CollectionOut])
def collections(response: Response, db: Session = Depends(get_db)) -> list[CollectionOut]:
    _cache(response)
    return catalogue.list_collections(db)


@router.get("/collections/{slug}", response_model=CollectionOut)
def collection(slug: str, response: Response, db: Session = Depends(get_db)) -> CollectionOut:
    _cache(response)
    return catalogue.get_collection(db, slug)


class ListingOut(BaseModel):
    """What `/collections/:slug` in the storefront shows: a category or a curated collection."""

    kind: Literal["category", "collection"]
    category: CategoryOut | None = None
    collection: CollectionOut | None = None


@router.get("/listings/{slug}", response_model=ListingOut)
def listing(slug: str, response: Response, db: Session = Depends(get_db)) -> ListingOut:
    _cache(response)
    try:
        return ListingOut(kind="category", category=catalogue.get_category(db, slug))
    except NotFound:
        return ListingOut(kind="collection", collection=catalogue.get_collection(db, slug))


@router.get("/products", response_model=Page[ProductCardOut])
def products(
    response: Response,
    filters: ProductFilters = Depends(product_filters),
    db: Session = Depends(get_db),
) -> Page[ProductCardOut]:
    _cache(response)
    items, total = catalogue.list_products(db, filters)
    return Page[ProductCardOut](
        items=items,
        page=filters.page,
        page_size=filters.page_size,
        total=total,
        pages=catalogue.page_count(total, filters.page_size),
    )


@router.get("/products/facets", response_model=FacetsOut)
def product_facets(
    response: Response,
    filters: ProductFilters = Depends(product_filters),
    db: Session = Depends(get_db),
) -> FacetsOut:
    _cache(response)
    return catalogue.facets(db, filters)


@router.get("/products/{slug}", response_model=ProductDetailOut)
def product_detail(
    slug: str, response: Response, db: Session = Depends(get_db)
) -> ProductDetailOut:
    _cache(response)
    return catalogue.get_product_detail(db, slug)


@router.get("/products/{slug}/related", response_model=list[ProductCardOut])
def related(slug: str, response: Response, db: Session = Depends(get_db)) -> list[ProductCardOut]:
    _cache(response)
    return catalogue.related_products(db, slug)


@router.get("/search/suggest", response_model=SuggestOut)
def suggest(
    response: Response,
    q: Annotated[str, Query(max_length=200)] = "",
    db: Session = Depends(get_db),
) -> SuggestOut:
    _cache(response)
    return catalogue.suggest(db, q)
