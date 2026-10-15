"""Public catalogue API: filters, sorting, search, pagination, facets, detail, listings, home."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Category, GoldRate, Product, ProductVariant
from app.services import inventory
from app.services.catalogue import refresh_price_cache

API = "/api/v1"


def names(response_json: dict) -> list[str]:  # type: ignore[type-arg]
    return [p["name"] for p in response_json["items"]]


def get_products(client: TestClient, **params: object) -> dict:  # type: ignore[type-arg]
    response = client.get(f"{API}/products", params=params)  # type: ignore[arg-type]
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore[no-any-return]


def make_product(db: Session, slug: str, status: str = "active", purity: str = "22K") -> Product:
    category = db.scalar(select(Category).where(Category.slug == "rings"))
    assert category is not None
    product = Product(
        slug=slug,
        name=f"Test {slug}",
        category_id=category.id,
        status=status,
        purity=purity,
        pricing_model="weight_based",
        making_charge_type="percent",
        making_charge_value=Decimal("10"),
    )
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku=f"T-{slug}"[:40],
        gross_weight_g=Decimal("2"),
        net_gold_weight_g=Decimal("2"),
        is_default=True,
    )
    db.add(variant)
    db.flush()
    inventory.set_initial_stock(db, variant.id, 3)
    db.flush()
    return product


# ------------------------------------------------------------------ listing & filters


def test_lists_only_active_products(client: TestClient, db: Session) -> None:
    make_product(db, "draft-piece", status="draft")
    make_product(db, "archived-piece", status="archived")
    db.commit()
    body = get_products(client, page_size=48)
    assert body["total"] == 31
    slugs = {p["slug"] for p in body["items"]}
    assert "draft-piece" not in slugs and "archived-piece" not in slugs
    assert client.get(f"{API}/products/draft-piece").status_code == 404


@pytest.mark.parametrize(
    ("params", "expected_total"),
    [
        ({"category": "rings"}, 4),
        ({"collection": "temple-classics"}, 5),
        ({"purity": "18K"}, 11),
        ({"purity": ["14K", "24K"]}, 4),
        ({"metal_colour": "rose"}, 4),
        ({"attr": "occasion:wedding"}, 7),
        ({"attr": ["occasion:wedding", "style:minimal"]}, 1),
        ({"category": "rings", "purity": "22K"}, 2),
    ],
)
def test_filters_narrow_results(
    client: TestClient, params: dict[str, object], expected_total: int
) -> None:
    body = get_products(client, page_size=48, **params)
    assert body["total"] == expected_total
    assert len(body["items"]) == expected_total


def test_slug_filter_returns_requested_products(client: TestClient) -> None:
    body = get_products(client, slug=["om-pendant", "rope-chain", "missing"])
    assert {p["slug"] for p in body["items"]} == {"om-pendant", "rope-chain"}
    too_many = client.get(f"{API}/products", params={"slug": [f"s{i}" for i in range(49)]})
    assert too_many.status_code == 422


def test_in_stock_filter_excludes_sold_out_products(client: TestClient) -> None:
    everything = get_products(client, page_size=48)
    in_stock = get_products(client, page_size=48, in_stock="true")
    sold_out = {p["slug"] for p in everything["items"] if p["stock_status"] == "out_of_stock"}
    assert sold_out == {"peacock-drops", "ganesha-pendant"}
    assert in_stock["total"] == everything["total"] - len(sold_out)


def test_price_range_filter(client: TestClient) -> None:
    body = get_products(client, page_size=48, min_price="20000", max_price="40000")
    assert body["total"] > 0
    for item in body["items"]:
        assert Decimal("20000") <= Decimal(item["price"]["amount"]) <= Decimal("40000")


def test_invalid_filters_are_rejected(client: TestClient) -> None:
    for params in (
        {"purity": "99K"},
        {"attr": "nocolon"},
        {"min_price": "5", "max_price": "1"},
        {"sort": "random"},
        {"page_size": "500"},
    ):
        response = client.get(f"{API}/products", params=params)
        assert response.status_code == 422, params
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_category_or_collection_is_404(client: TestClient) -> None:
    assert client.get(f"{API}/products", params={"category": "nope"}).status_code == 404
    assert client.get(f"{API}/products", params={"collection": "nope"}).status_code == 404


# ------------------------------------------------------------------ sorting & pagination


@pytest.mark.parametrize("sort", ["price_asc", "price_desc"])
def test_price_sorting(client: TestClient, sort: str) -> None:
    prices = [
        Decimal(p["price"]["amount"])
        for p in get_products(client, sort=sort, page_size=48)["items"]
    ]
    assert prices == sorted(prices, reverse=(sort == "price_desc"))


def test_newest_sorting(client: TestClient) -> None:
    items = get_products(client, sort="newest", page_size=3)["items"]
    assert [p["slug"] for p in items] == [
        "twisted-singapore-chain",
        "initial-disc-pendant",
        "rose-twist-ring",
    ]


def test_pagination(client: TestClient) -> None:
    page1 = get_products(client, page_size=10, page=1, sort="price_asc")
    page4 = get_products(client, page_size=10, page=4, sort="price_asc")
    beyond = get_products(client, page_size=10, page=9)
    assert page1["pages"] == 4 and len(page1["items"]) == 10
    assert len(page4["items"]) == 1
    assert beyond["items"] == [] and beyond["total"] == 31


# ------------------------------------------------------------------ search


def test_search_by_name_category_and_sku(client: TestClient) -> None:
    assert "Meenakshi Jhumkas" in names(get_products(client, q="jhumkas"))
    assert get_products(client, q="ANV-RG-002")["items"][0]["slug"] == "everyday-gold-band"
    assert get_products(client, q="bangles")["total"] >= 4


@pytest.mark.parametrize(
    "q",
    [
        "%",
        "_",
        "100%_gold",
        "'; DROP TABLE products; --",
        '"quoted"',
        "💍 ring",
        "a" * 200,
        "\\",
        "-",
        "OR",
        "ring OR",
    ],
)
def test_search_handles_hostile_input(client: TestClient, q: str) -> None:
    response = client.get(f"{API}/products", params={"q": q})
    assert response.status_code == 200
    assert client.get(f"{API}/search/suggest", params={"q": q}).status_code == 200


def test_search_query_too_long_is_rejected(client: TestClient) -> None:
    assert client.get(f"{API}/products", params={"q": "a" * 201}).status_code == 422


def test_percent_does_not_match_everything(client: TestClient) -> None:
    assert get_products(client, q="%")["total"] == 0


def test_suggestions(client: TestClient) -> None:
    body = client.get(f"{API}/search/suggest", params={"q": "ring"}).json()
    # "ring" also matches "Earrings"; categories keep their display order.
    assert body["categories"] == [
        {"slug": "rings", "name": "Rings"},
        {"slug": "earrings", "name": "Earrings"},
    ]
    assert body["products"]
    assert client.get(f"{API}/search/suggest", params={"q": "r"}).json() == {
        "products": [],
        "categories": [],
    }


# ------------------------------------------------------------------ facets


def test_facets_for_category(client: TestClient) -> None:
    body = client.get(f"{API}/products/facets", params={"category": "rings"}).json()
    assert body["total"] == 4
    assert {f["value"]: f["count"] for f in body["purities"]} == {"22K": 2, "18K": 1, "14K": 1}
    assert set(body["attributes"]) == {"occasion", "style"}
    assert Decimal(body["price_min"]) <= Decimal(body["price_max"])
    assert body["in_stock_count"] == 4


def test_facets_for_a_search(client: TestClient) -> None:
    """Regression: the category facet crashed (500) when combined with a search query."""
    products = client.get(f"{API}/products", params={"q": "ring"}).json()
    response = client.get(f"{API}/products/facets", params={"q": "ring"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == products["total"] > 0
    assert sum(c["count"] for c in body["categories"]) == body["total"]
    # A category-name match ("Rings") counts too, and search within a category works.
    within = client.get(f"{API}/products/facets", params={"q": "ring", "category": "rings"})
    assert within.status_code == 200 and within.json()["total"] >= 1


# ------------------------------------------------------------------ product detail


def test_product_detail_with_variant_breakdowns(client: TestClient) -> None:
    body = client.get(f"{API}/products/everyday-gold-band").json()
    assert body["category"] == {"slug": "rings", "name": "Rings"}
    assert body["hallmark_details"] is None and body["certification_details"] is None
    assert body["is_sample"] is True
    assert [v["label"] for v in body["variants"]] == ["Size 10", "Size 12", "Size 14", "Size 16"]
    size12 = body["variants"][1]
    assert size12["is_default"] is True
    rows = size12["price"]["breakdown"]
    assert sum(Decimal(r["amount"]) for r in rows[:-1]) == Decimal(rows[-1]["amount"])
    assert rows[-1]["amount"] == size12["price"]["amount"] == "27402.74"
    assert size12["price"]["gold_rate"]["purity"] == "22K"
    assert size12["price"]["gold_rate"]["effective_from"].endswith(("Z", "+00:00"))


def test_variant_stock_statuses(client: TestClient) -> None:
    body = client.get(f"{API}/products/aria-solitaire-ring").json()
    statuses = {v["label"]: (v["stock_status"], v["available_quantity"]) for v in body["variants"]}
    assert statuses == {
        "Size 10": ("in_stock", 3),
        "Size 12": ("in_stock", 5),
        "Size 14": ("low_stock", 2),
        "Size 16": ("out_of_stock", 0),
    }


def test_product_without_gold_rate_cannot_be_priced(client: TestClient, db: Session) -> None:
    db.execute(delete(GoldRate).where(GoldRate.purity == "14K"))
    db.commit()
    body = client.get(f"{API}/products/rose-twist-ring").json()
    price = body["variants"][0]["price"]
    assert price["available"] is False
    assert price["unavailable_reason"] == "NO_GOLD_RATE"
    assert price["amount"] is None
    # Fixed-price 14K items are unaffected by gold rates.
    fixed = client.get(f"{API}/products/initial-disc-pendant").json()
    assert fixed["variants"][0]["price"]["available"] is True


def test_price_cache_follows_new_gold_rate(client: TestClient, db: Session) -> None:
    from app.core.time import utcnow

    before = Decimal(
        client.get(f"{API}/products/om-pendant").json()["variants"][0]["price"]["amount"]
    )
    db.add(
        GoldRate(
            purity="22K",
            rate_per_gram=Decimal("8000.00"),
            effective_from=utcnow(),
            source_note="test",
        )
    )
    db.flush()
    refresh_price_cache(db)
    db.commit()
    after = Decimal(
        client.get(f"{API}/products/om-pendant").json()["variants"][0]["price"]["amount"]
    )
    assert after > before
    cached = db.scalar(select(Product.price_from).where(Product.slug == "om-pendant"))
    assert cached == after


def test_unknown_product_is_404(client: TestClient) -> None:
    response = client.get(f"{API}/products/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_related_products_exclude_self(client: TestClient) -> None:
    body = client.get(f"{API}/products/everyday-gold-band/related").json()
    assert body and all(p["slug"] != "everyday-gold-band" for p in body)
    assert all(p["category"]["slug"] == "rings" for p in body)


# ------------------------------------------------------------------ categories, listings, home


def test_listing_resolves_category_and_collection(client: TestClient) -> None:
    assert client.get(f"{API}/listings/rings").json()["kind"] == "category"
    collection = client.get(f"{API}/listings/bridal-heirlooms").json()
    assert collection["kind"] == "collection"
    assert collection["collection"]["name"] == "Bridal Heirlooms"
    assert client.get(f"{API}/listings/nothing-here").status_code == 404


def test_categories_and_collections(client: TestClient) -> None:
    assert len(client.get(f"{API}/categories").json()) == 8
    first = client.get(f"{API}/collections").json()[0]
    assert first["slug"] == "everyday-gold"


def test_home_sections(client: TestClient) -> None:
    body = client.get(f"{API}/home").json()
    assert len(body["categories"]) == 8
    assert len(body["collections"]) == 3  # only featured collections
    assert len(body["new_arrivals"]) == 8
    assert all(p["is_sample"] for p in body["bestsellers"])
    assert body["featured"]


def test_cards_flag_products_whose_sizes_differ_in_price(client: TestClient) -> None:
    items = {p["slug"]: p for p in get_products(client, page_size=48)["items"]}
    assert items["everyday-gold-band"]["price_is_from"] is True  # four ring sizes
    assert items["om-pendant"]["price_is_from"] is False  # single variant


def test_money_is_serialised_as_strings(client: TestClient) -> None:
    item = get_products(client, page_size=1)["items"][0]
    assert isinstance(item["price"]["amount"], str)
    assert isinstance(item["weight_g"], str)


def test_catalogue_responses_are_cacheable(client: TestClient) -> None:
    assert client.get(f"{API}/products").headers["cache-control"] == "public, max-age=60"
    detail = client.get(f"{API}/products/everyday-gold-band")
    assert detail.headers["cache-control"] == "no-cache"  # stock/price shown where people buy


def test_sitemap_lists_public_pages(client: TestClient) -> None:
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "http://localhost:5180/products/everyday-gold-band" in response.text
    assert "http://localhost:5180/collections/rings" in response.text
    assert "/refund-policy" in response.text


def test_robots_blocks_everything_until_indexing_is_allowed(
    client: TestClient, app: FastAPI, settings: Settings
) -> None:
    closed = client.get("/robots.txt")
    assert closed.status_code == 200
    assert closed.headers["content-type"].startswith("text/plain")
    assert "Disallow: /" in closed.text.splitlines() and "Sitemap" not in closed.text

    app.state.settings = settings.model_copy(update={"allow_search_indexing": True})
    lines = client.get("/robots.txt").text.splitlines()
    for private in ("/admin", "/account", "/checkout", "/cart", "/order-confirmation", "/api/"):
        assert f"Disallow: {private}" in lines
    assert "Disallow: /" not in lines
    assert "Sitemap: http://localhost:5180/sitemap.xml" in lines
