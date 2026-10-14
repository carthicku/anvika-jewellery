# Phase 3 — Database-backed Catalogue  ✅ complete (2026-10-14)

Goal: the storefront shows real products from PostgreSQL with working filters, sorting, search and
pagination.

## Tasks
- [x] Models + migration: categories, collections, collection_products, products (+ generated search_vector,
      GIN index), product_variants, product_images, product_attributes, inventory_levels,
      inventory_movements, gold_rates, discounts, store_settings, content_pages, shipping_methods,
      shipping_zones, newsletter_subscribers, contact_enquiries, audit_logs, rate_limit_buckets
- [x] RLS-enable statement for all tables in migrations
- [x] Pricing engine core (pure functions) — needed to show prices; unit-tested with the worked example
- [x] Price cache (`products.price_from`) refresh service
- [x] Public APIs: `/home`, `/categories`, `/collections`, `/products` (filters, sort, pagination),
      `/products/facets`, `/products/{slug}`, `/products/{slug}/related`, `/search/suggest`,
      `/settings/public`, `/content/{slug}`, `/shipping/pincode/{pin}`
- [x] `/contact` + `/newsletter/*` with validation, honeypot and rate limiting
- [x] Deterministic seed (`python -m app.cli seed`) per SEED_DATA.md, incl. placeholder images
- [x] `/sitemap.xml`
- [x] Export OpenAPI + generate frontend types
- [x] API tests: drafts hidden, each filter, sorts, pagination, special-character search, facets, contact
      validation/rate-limit, pincode
- [x] Frontend wired (Phase 2 pages) and component tests updated

## Acceptance
Filters/sort/search change results; URL reproduces state; tests green.

Notes: the PIN-code check API and the full pricing engine (discounts, coupons, rounding) were
built here rather than in Phase 5 because product pages need them. The price cache refreshes on
seed and via `python -m app.cli refresh-prices`; the scheduled refresh arrives with the background
jobs in Phase 6.
