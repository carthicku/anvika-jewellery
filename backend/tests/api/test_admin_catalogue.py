"""Admin catalogue API: products and variants, publishing rules, photo uploads (re-encoding,
metadata stripping, rejection of bad files), price preview, categories, collections (J8)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from botocore.stub import Stubber
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import AuditLog, Category, InventoryLevel, ProductVariant
from app.services.storage import LocalStorage, S3Storage
from tests.conftest import login_client

API = "/api/v1/admin"


@pytest.fixture()
def staff(app: FastAPI, make_user, tmp_path: Path) -> TestClient:  # type: ignore[no-untyped-def]
    app.state.storage = LocalStorage(tmp_path, base_url="/media")
    make_user(email="cat@example.com", role="staff", full_name="Catalogue Staff")
    with TestClient(app, base_url="http://testserver") as c:
        c.headers["X-CSRF-Token"] = c.get("/api/v1/auth/csrf").json()["csrf_token"]
        yield login_client(c, "cat@example.com")


def category_id(db: Session, slug: str = "rings") -> str:
    found = db.scalar(select(Category.id).where(Category.slug == slug))
    assert found is not None
    return str(found)


def product_body(db: Session, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "Test Lotus Ring",
        "category_id": category_id(db),
        "purity": "22K",
        "pricing_model": "weight_based",
        "making_charge_type": "percent",
        "making_charge_value": "12.00",
        "description": "A test ring.",
        "attributes": [{"key": "occasion", "value": "daily"}],
        "variants": [
            {
                "sku": "TST-LOTUS-12",
                "label": "Size 12",
                "size": "12",
                "net_gold_weight_g": "4.000",
                "gross_weight_g": "4.100",
                "initial_stock": 3,
            },
            {
                "sku": "TST-LOTUS-14",
                "label": "Size 14",
                "size": "14",
                "net_gold_weight_g": "4.200",
                "initial_stock": 0,
            },
        ],
    }
    body.update(overrides)
    return body


def png(
    width: int = 1000, height: int = 1200, fmt: str = "PNG", exif: bytes | None = None
) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (width, height), (212, 175, 55))
    if exif is not None:
        image.save(buffer, fmt, exif=exif)
    else:
        image.save(buffer, fmt)
    return buffer.getvalue()


# ------------------------------------------------------------------ products


def test_create_draft_product_with_variants_and_stock(
    staff: TestClient, client: TestClient, db: Session
) -> None:
    response = staff.post(f"{API}/products", json=product_body(db))
    assert response.status_code == 201, response.text
    product = response.json()
    assert product["slug"] == "test-lotus-ring"
    assert product["status"] == "draft"
    assert [v["sku"] for v in product["variants"]] == ["TST-LOTUS-12", "TST-LOTUS-14"]
    first = product["variants"][0]
    assert first["is_default"] is True and first["on_hand"] == 3
    # 4 g × ₹7,150 (illustrative seed rate) = 28,600 + 12% making 3,432 + 3% GST = 32,992.96
    assert first["unit_price"] == "32992.96"
    assert product["publish_problems"] == []
    assert product["attributes"] == [{"key": "occasion", "value": "daily"}]
    # Drafts are invisible to customers.
    assert client.get("/api/v1/products/test-lotus-ring").status_code == 404
    log = db.scalar(select(AuditLog).where(AuditLog.action == "product.create"))
    assert log is not None and log.changes["skus"] == ["TST-LOTUS-12", "TST-LOTUS-14"]


def test_publish_then_archive(staff: TestClient, client: TestClient, db: Session) -> None:
    created = staff.post(f"{API}/products", json=product_body(db)).json()
    body = {k: v for k, v in product_body(db).items() if k != "variants"}
    published = staff.put(f"{API}/products/{created['id']}", json={**body, "status": "active"})
    assert published.status_code == 200, published.text
    assert published.json()["published_at"] is not None
    storefront = client.get("/api/v1/products/test-lotus-ring")
    assert storefront.status_code == 200
    assert storefront.json()["name"] == "Test Lotus Ring"

    staff.put(f"{API}/products/{created['id']}", json={**body, "status": "archived"})
    assert client.get("/api/v1/products/test-lotus-ring").status_code == 404


def test_pricing_inputs_are_required_by_model(staff: TestClient, db: Session) -> None:
    weightless = product_body(db)
    weightless["variants"][0].pop("net_gold_weight_g")
    weightless["variants"][0].pop("gross_weight_g")
    response = staff.post(f"{API}/products", json=weightless)
    assert response.status_code == 422
    assert "variants.0.net_gold_weight_g" in response.json()["error"]["details"]["fields"]

    fixed = product_body(db, pricing_model="fixed", making_charge_type="none")
    response = staff.post(f"{API}/products", json=fixed)
    assert response.status_code == 422
    assert "variants.0.fixed_price" in response.json()["error"]["details"]["fields"]


def test_net_weight_cannot_exceed_gross(staff: TestClient, db: Session) -> None:
    body = product_body(db)
    body["variants"][0]["gross_weight_g"] = "3.000"
    assert staff.post(f"{API}/products", json=body).status_code == 422


def test_duplicate_sku_and_slug_are_refused(staff: TestClient, db: Session) -> None:
    body = product_body(db)
    body["variants"][1]["sku"] = "ANV-RG-002-12"  # a seeded SKU
    assert staff.post(f"{API}/products", json=body).status_code == 422
    clash = product_body(db, slug="everyday-gold-band")
    response = staff.post(f"{API}/products", json=clash)
    assert response.status_code == 422
    assert "slug" in response.json()["error"]["details"]["fields"]
    # Without an explicit slug, a free one is chosen.
    staff.post(f"{API}/products", json=product_body(db))
    second = product_body(db)
    second["variants"] = [{**v, "sku": v["sku"] + "B"} for v in second["variants"]]
    assert staff.post(f"{API}/products", json=second).json()["slug"] == "test-lotus-ring-2"


def test_browser_cannot_set_customer_prices(staff: TestClient, db: Session) -> None:
    body = product_body(db)
    body["variants"][0]["unit_price"] = "1.00"
    assert staff.post(f"{API}/products", json=body).status_code == 422
    assert (
        staff.post(f"{API}/products", json={**product_body(db), "price_from": "1"}).status_code
        == 422
    )


def test_variants_can_be_added_updated_and_deactivated(staff: TestClient, db: Session) -> None:
    product = staff.post(f"{API}/products", json=product_body(db)).json()
    added = staff.post(
        f"{API}/products/{product['id']}/variants",
        json={
            "sku": "TST-LOTUS-16",
            "label": "Size 16",
            "net_gold_weight_g": "4.400",
            "initial_stock": 2,
            "is_default": True,
        },
    )
    assert added.status_code == 201, added.text
    variants = {v["sku"]: v for v in added.json()["variants"]}
    assert variants["TST-LOTUS-16"]["is_default"] is True
    assert variants["TST-LOTUS-12"]["is_default"] is False
    level = db.scalar(
        select(InventoryLevel)
        .join(ProductVariant, ProductVariant.id == InventoryLevel.variant_id)
        .where(ProductVariant.sku == "TST-LOTUS-16")
    )
    assert level is not None and level.on_hand == 2

    vid = variants["TST-LOTUS-14"]["id"]
    updated = staff.put(
        f"{API}/products/{product['id']}/variants/{vid}",
        json={
            "sku": "TST-LOTUS-14",
            "label": "Size 14",
            "net_gold_weight_g": "4.250",
            "is_active": False,
        },
    )
    v14 = next(v for v in updated.json()["variants"] if v["id"] == vid)
    assert v14["is_active"] is False and v14["net_gold_weight_g"] == "4.250"


# ------------------------------------------------------------------ photos


def test_photo_upload_is_reencoded_in_several_sizes(
    staff: TestClient, db: Session, tmp_path: Path
) -> None:
    product = staff.post(f"{API}/products", json=product_body(db)).json()
    exif = Image.Exif()
    exif[0x010F] = "SecretCamera"  # Make
    exif[0x8825] = {2: (12, 58, 0)}  # GPS info
    jpeg = png(fmt="JPEG", exif=exif.tobytes())
    response = staff.post(
        f"{API}/products/{product['id']}/images",
        files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        data={"alt_text": "Lotus ring on a velvet tray"},
    )
    assert response.status_code == 201, response.text
    image = response.json()["images"][0]
    assert image["alt_text"] == "Lotus ring on a velvet tray"
    assert sorted(int(w) for w in image["renditions"]) == [400, 800, 1000]
    assert image["url"].startswith("/media/products/") and image["url"].endswith("-1000.webp")
    assert "photo" not in image["url"]  # never the uploader's file name
    stored = tmp_path / image["url"].removeprefix("/media/")
    with Image.open(stored) as saved:
        assert saved.format == "WEBP"
        assert saved.size == (1000, 1200)
        assert not saved.getexif()  # camera and GPS metadata removed


@pytest.mark.parametrize(
    ("name", "content", "mime"),
    [
        ("notes.txt", b"hello, not an image", "text/plain"),
        ("evil.jpg", b"<script>alert(1)</script>", "image/jpeg"),
        ("tiny.png", png(100, 100), "image/png"),
        ("anim.gif", png(fmt="GIF"), "image/gif"),
    ],
)
def test_bad_uploads_are_rejected(
    staff: TestClient, db: Session, name: str, content: bytes, mime: str
) -> None:
    product = staff.post(f"{API}/products", json=product_body(db)).json()
    response = staff.post(
        f"{API}/products/{product['id']}/images", files={"file": (name, content, mime)}
    )
    assert response.status_code == 422
    assert "file" in response.json()["error"]["details"]["fields"]


def test_photos_can_be_described_reordered_and_deleted(
    staff: TestClient, db: Session, tmp_path: Path
) -> None:
    product = staff.post(f"{API}/products", json=product_body(db)).json()
    url = f"{API}/products/{product['id']}/images"
    staff.post(url, files={"file": ("a.png", png(), "image/png")})
    images = staff.post(url, files={"file": ("b.png", png(800, 800), "image/png")}).json()["images"]
    first, second = images[0]["id"], images[1]["id"]

    alt = staff.patch(f"{url}/{first}", json={"alt_text": "Front view"}).json()["images"][0]
    assert alt["alt_text"] == "Front view"
    reordered = staff.put(f"{url}/order", json={"image_ids": [second, first]}).json()["images"]
    assert [i["id"] for i in reordered] == [second, first]
    assert staff.put(f"{url}/order", json={"image_ids": [first]}).status_code == 422

    files_before = list(tmp_path.rglob("*.webp"))
    remaining = staff.delete(f"{url}/{second}").json()["images"]
    assert [i["id"] for i in remaining] == [first]
    assert len(list(tmp_path.rglob("*.webp"))) < len(files_before)


def test_s3_storage_uploads_with_long_cache(make_settings) -> None:  # type: ignore[no-untyped-def]
    import boto3

    settings: Settings = make_settings(
        storage_backend="s3",
        s3_bucket="media-bucket",
        s3_public_base_url="https://cdn.example.com/media",
        s3_region="ap-south-1",
    )
    client = boto3.client(
        "s3", region_name="ap-south-1", aws_access_key_id="x", aws_secret_access_key="y"
    )
    with Stubber(client) as stub:
        stub.add_response(
            "put_object",
            {},
            {
                "Bucket": "media-bucket",
                "Key": "products/p1/abc-400.webp",
                "Body": b"data",
                "ContentType": "image/webp",
                "CacheControl": "public, max-age=31536000, immutable",
            },
        )
        url = S3Storage(settings, client=client).save(
            "products/p1/abc-400.webp", b"data", "image/webp"
        )
    assert url == "https://cdn.example.com/media/products/p1/abc-400.webp"
    with pytest.raises(ValueError):
        S3Storage(settings, client=client).save("../etc/passwd", b"x", "text/plain")


# ------------------------------------------------------------------ preview, categories, collections


def test_price_preview_uses_current_rate_and_saves_nothing(staff: TestClient) -> None:
    response = staff.post(
        f"{API}/catalogue/price-preview",
        json={
            "purity": "22K",
            "pricing_model": "weight_based",
            "making_charge_type": "percent",
            "making_charge_value": "12.00",
            "variants": [{"label": "4 g", "net_gold_weight_g": "4.000"}, {"label": "No weight"}],
        },
    ).json()
    assert response["gold_rate_per_gram"] == "7150.00"
    assert response["variants"][0]["total"] == "32992.96"
    rows = response["variants"][0]["breakdown"]
    assert rows[0]["amount"] == "28600.00"
    assert response["variants"][1]["total"] is None
    assert "net gold weight" in response["variants"][1]["error"]


def test_categories_crud_with_safety(staff: TestClient, db: Session) -> None:
    created = staff.post(
        f"{API}/categories", json={"name": "Nose Pins", "parent_id": None, "sort_order": 9}
    )
    assert created.status_code == 201, created.text
    nose = created.json()
    assert nose["slug"] == "nose-pins" and nose["product_count"] == 0
    child = staff.post(f"{API}/categories", json={"name": "Studs", "parent_id": nose["id"]}).json()
    grandchild = staff.post(f"{API}/categories", json={"name": "Tiny", "parent_id": child["id"]})
    assert grandchild.status_code == 422  # one level deep only
    in_use = staff.delete(f"{API}/categories/{category_id(db, 'rings')}")
    assert in_use.status_code == 409 and in_use.json()["error"]["code"] == "CATEGORY_IN_USE"
    assert staff.delete(f"{API}/categories/{nose['id']}").status_code == 409  # has a child
    assert staff.delete(f"{API}/categories/{child['id']}").status_code == 200
    assert staff.delete(f"{API}/categories/{nose['id']}").status_code == 200


def test_collections_hold_ordered_products(staff: TestClient, db: Session) -> None:
    a = staff.post(f"{API}/products", json=product_body(db)).json()
    body = product_body(db, name="Test Second")
    body["variants"] = [{**v, "sku": v["sku"] + "X"} for v in body["variants"]]
    b = staff.post(f"{API}/products", json=body).json()
    created = staff.post(
        f"{API}/collections", json={"name": "Festive Edit", "product_ids": [b["id"], a["id"]]}
    )
    assert created.status_code == 201, created.text
    assert created.json()["product_ids"] == [b["id"], a["id"]]
    unknown = staff.put(
        f"{API}/collections/{created.json()['id']}",
        json={"name": "Festive Edit", "product_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert unknown.status_code == 422
    product = staff.get(f"{API}/products/{a['id']}").json()
    assert product["collection_ids"] == [created.json()["id"]]


def test_customers_cannot_manage_the_catalogue(
    other_client: TestClient, db: Session, make_user
) -> None:  # type: ignore[no-untyped-def]
    make_user(email="shopper@example.com")
    login_client(other_client, "shopper@example.com")
    assert other_client.post(f"{API}/products", json=product_body(db)).status_code == 403
    assert other_client.get(f"{API}/products").status_code == 403


def test_product_list_search_by_sku(staff: TestClient) -> None:
    rows = staff.get(f"{API}/products", params={"q": "ANV-RG-002"}).json()["items"]
    assert [r["slug"] for r in rows] == ["everyday-gold-band"]
    assert rows[0]["available"] > 0 and rows[0]["is_sample"] is True
