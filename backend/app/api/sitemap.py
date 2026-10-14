"""XML sitemap of public storefront pages, served at /sitemap.xml (the web server proxies it)."""

from __future__ import annotations

from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Category, Collection, ContentPage, Product

router = APIRouter(include_in_schema=False)

# Content slugs that map to storefront routes (see frontend router).
CONTENT_ROUTES = {
    "about": "/about",
    "faq": "/faq",
    "jewellery-care": "/jewellery-care",
    "gold-buying-guide": "/gold-buying-guide",
    "shipping-policy": "/shipping-policy",
    "returns-and-exchanges": "/returns-and-exchanges",
    "privacy-policy": "/privacy-policy",
    "terms-and-conditions": "/terms-and-conditions",
    "refund-policy": "/refund-policy",
}


@router.get("/sitemap.xml")
def sitemap(request: Request, db: Session = Depends(get_db)) -> Response:
    base = request.app.state.settings.public_site_url.rstrip("/")
    entries: list[tuple[str, str | None]] = [
        ("/", None),
        ("/collections", None),
        ("/contact", None),
    ]
    entries += [
        (f"/collections/{slug}", None)
        for slug in db.scalars(select(Category.slug).where(Category.is_active)).all()
    ]
    entries += [
        (f"/collections/{slug}", None)
        for slug in db.scalars(select(Collection.slug).where(Collection.is_active)).all()
    ]
    for slug, updated in db.execute(
        select(Product.slug, Product.updated_at).where(Product.status == "active")
    ).all():
        entries.append((f"/products/{slug}", updated.date().isoformat()))
    for slug, updated in db.execute(select(ContentPage.slug, ContentPage.updated_at)).all():
        if slug in CONTENT_ROUTES:
            entries.append((CONTENT_ROUTES[slug], updated.date().isoformat()))

    urls = []
    for path, lastmod in entries:
        loc = f"<loc>{escape(base + path)}</loc>"
        mod = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        urls.append(f"<url>{loc}{mod}</url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls)
        + "</urlset>\n"
    )
    return Response(
        content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"}
    )
