"""Catalogue API timing with ~1,000 products (docs/quality/PERFORMANCE_REVIEW.md).

Runs against a SEPARATE database whose name ends in `_perf` (it refuses anything else), because it
adds hundreds of copies of the sample products. Create and fill it once:

    # backend/, with the local PostgreSQL running
    set DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:54329/anvika_perf
    (create the database, then) .venv/Scripts/python -m alembic upgrade head
    .venv/Scripts/python -m app.cli seed
    .venv/Scripts/python ../scripts/perf_catalogue.py --target 1000

It times each public catalogue endpoint in-process (no network: this measures the app and the
database, not the internet) and prints p50/p95, plus EXPLAIN ANALYZE for the listing query.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import func, insert, select, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db import make_engine, make_session_factory  # noqa: E402
from app.models import (  # noqa: E402
    InventoryLevel,
    Product,
    ProductAttribute,
    ProductImage,
    ProductVariant,
)
from app.services.catalogue import refresh_price_cache  # noqa: E402


def _row(obj: object, skip: set[str]) -> dict[str, object]:
    table = obj.__table__  # type: ignore[attr-defined]
    return {
        c.key: getattr(obj, c.key)
        for c in table.columns
        if c.key not in skip and c.computed is None and c.key != "id"
    }


def fill(db, target: int) -> int:  # type: ignore[no-untyped-def]
    originals = list(
        db.scalars(select(Product).where(Product.is_sample, Product.status == "active"))
    )
    have = db.scalar(select(func.count()).select_from(Product).where(Product.status == "active"))
    copy = 0
    while have < target:
        copy += 1
        for product in originals:
            if have >= target:
                break
            slug = f"{product.slug}-perf-{copy}"
            if db.scalar(select(Product.id).where(Product.slug == slug)):
                continue
            new_id = db.execute(
                insert(Product)
                .values(
                    **_row(product, {"slug", "name", "created_at", "updated_at"}),
                    slug=slug,
                    name=f"{product.name} {copy}",
                )
                .returning(Product.id)
            ).scalar_one()
            for variant in db.scalars(
                select(ProductVariant).where(ProductVariant.product_id == product.id)
            ):
                vid = db.execute(
                    insert(ProductVariant)
                    .values(
                        **_row(variant, {"product_id", "sku", "created_at", "updated_at"}),
                        product_id=new_id,
                        sku=f"{variant.sku}-P{copy}",
                    )
                    .returning(ProductVariant.id)
                ).scalar_one()
                level = db.get(InventoryLevel, variant.id)
                if level is not None:
                    db.execute(
                        insert(InventoryLevel).values(
                            **_row(level, {"variant_id", "updated_at"}), variant_id=vid
                        )
                    )
            for image in db.scalars(
                select(ProductImage).where(ProductImage.product_id == product.id)
            ):
                db.execute(
                    insert(ProductImage).values(
                        **_row(image, {"product_id", "created_at"}), product_id=new_id
                    )
                )
            for attr in db.scalars(
                select(ProductAttribute).where(ProductAttribute.product_id == product.id)
            ):
                db.execute(
                    insert(ProductAttribute).values(**_row(attr, {"product_id"}), product_id=new_id)
                )
            have += 1
    db.commit()
    refresh_price_cache(db)
    db.commit()
    db.execute(text("ANALYZE"))
    db.commit()
    return have


CASES = [
    ("listing (default)", "/api/v1/products"),
    ("listing, category + sort", "/api/v1/products?category=rings&sort=price_asc"),
    ("listing, filters", "/api/v1/products?purity=22K&in_stock=true&price_max=150000"),
    ("search", "/api/v1/products?q=gold%20ring"),
    ("facets (category)", "/api/v1/products/facets?category=rings"),
    ("facets (search)", "/api/v1/products/facets?q=ring"),
    ("product detail", "/api/v1/products/om-pendant"),
    ("home", "/api/v1/home"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", type=int, default=1000, help="active products to reach")
    parser.add_argument("--runs", type=int, default=60, help="requests per endpoint")
    args = parser.parse_args()

    settings = get_settings()
    name = make_url(settings.database_url).database or ""
    if not name.endswith("_perf"):
        print(f"Refusing to run against {name!r}: the database name must end in '_perf'.")
        return 2
    settings = settings.model_copy(
        update={"rate_limit_enabled": False, "background_jobs_enabled": False}
    )
    factory = make_session_factory(make_engine(settings.database_url))
    with factory() as db:
        total = fill(db, args.target)
    print(f"Active products: {total}")

    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app(settings)) as client:
        print(f"{'endpoint':28} {'p50 ms':>8} {'p95 ms':>8} {'max ms':>8}  status")
        for label, url in CASES:
            client.get(url)  # warm-up
            times, status = [], 0
            for _ in range(args.runs):
                start = time.perf_counter()
                response = client.get(url)
                times.append((time.perf_counter() - start) * 1000)
                status = response.status_code
            times.sort()
            p95 = times[int(len(times) * 0.95) - 1]
            print(
                f"{label:28} {statistics.median(times):8.1f} {p95:8.1f} {times[-1]:8.1f}  {status}"
            )

    with factory() as db:
        plan = db.execute(
            text(
                "EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM products WHERE status = 'active' "
                "ORDER BY published_at DESC NULLS LAST, id LIMIT 24"
            )
        ).scalars()
        print("\nEXPLAIN ANALYZE (default listing page):")
        for line in plan:
            print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
