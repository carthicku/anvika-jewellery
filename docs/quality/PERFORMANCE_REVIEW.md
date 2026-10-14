# Performance Review

Targets come from [PRODUCT_REQUIREMENTS.md §5](../PRODUCT_REQUIREMENTS.md). Record measurements
here with the date, tool, environment and numbers. Do not estimate.

## Planned measures
| Area | Approach |
|------|----------|
| JavaScript size | Route-level code splitting (admin and account chunks lazy-loaded); check `vite build` output sizes |
| Images | Uploads re-encoded to WebP at several widths (400/800/1200/1600) with `srcset`; lazy-loading below the fold; explicit `width`/`height` to prevent layout shift |
| Fonts | Self-hosted, Latin subset, `font-display: swap`, preload of the two most-used files |
| API | Indexed filters, `selectinload` for related rows, pagination, `price_from` cache for price sorting, HTTP caching headers on public catalogue GETs (`Cache-Control: public, max-age=60`) |
| Database | `EXPLAIN ANALYZE` of the listing and search queries with 1,000+ products (seed `--bulk` option) |
| SEO / SPA limits | The SPA renders on the client. Crawlers that run JavaScript (Google) index it. For others, pre-rendering of public routes is a future improvement (KNOWN_LIMITATIONS) |

## Measurements

### 2026-10-14 — Storefront bundle (Vite 8 production build)
| Chunk | Size | Gzip |
|-------|-----:|-----:|
| Initial bundle (`index-*.js`, home page + layout) | 479 kB | **150 kB** (target < 200 kB ✅) |
| Content pages (Markdown renderer) | 156 kB | 47 kB (loaded only on content pages) |
| Contact page (form + validation libraries) | 119 kB | 37 kB |
| Product page | 15 kB | 5 kB |
| Listing pages | 15 kB | 5 kB |

Actions taken: route-level code splitting (all routes except home are lazy); the footer newsletter
form was rewritten without zod/react-hook-form so those libraries stay out of the initial bundle
(initial bundle 248 kB → 150 kB gzip).

Not yet measured: Lighthouse/Core Web Vitals and API latency under load (Phase 8).
