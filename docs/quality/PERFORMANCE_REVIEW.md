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
_None yet (Phase 0)._
