# Phase 3 — Database-backed Catalogue

Goal: the storefront shows real products from PostgreSQL with working filters, sorting, search and
pagination.

## Tasks
- [ ] Models + migration: categories, collections, collection_products, products (+ generated search_vector,
      GIN index), product_variants, product_images, product_attributes, inventory_levels,
      inventory_movements, gold_rates, discounts, store_settings, content_pages, shipping_methods,
      shipping_zones, newsletter_subscribers, contact_enquiries, audit_logs, rate_limit_buckets
- [ ] RLS-enable statement for all tables in migrations
- [ ] Pricing engine core (pure functions) — needed to show prices; unit-tested with the worked example
- [ ] Price cache (`products.price_from`) refresh service
- [ ] Public APIs: `/home`, `/categories`, `/collections`, `/products` (filters, sort, pagination),
      `/products/facets`, `/products/{slug}`, `/products/{slug}/related`, `/search/suggest`,
      `/settings/public`, `/content/{slug}`, `/shipping/pincode/{pin}`
- [ ] `/contact` + `/newsletter/*` with validation, honeypot and rate limiting
- [ ] Deterministic seed (`python -m app.cli seed`) per SEED_DATA.md, incl. placeholder images
- [ ] `/sitemap.xml`
- [ ] Export OpenAPI + generate frontend types
- [ ] API tests: drafts hidden, each filter, sorts, pagination, special-character search, facets, contact
      validation/rate-limit, pincode
- [ ] Frontend wired (Phase 2 pages) and component tests updated

## Acceptance
Filters/sort/search change results; URL reproduces state; tests green.
