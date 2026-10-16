# Performance Review

Targets come from [PRODUCT_REQUIREMENTS.md §5](../PRODUCT_REQUIREMENTS.md). Record measurements
here with the date, tool, environment and numbers. Do not estimate.

## Planned measures
| Area | Approach |
|------|----------|
| JavaScript size | Route-level code splitting (admin and account chunks lazy-loaded); check `vite build` output sizes |
| Images | Uploads re-encoded to WebP at several widths (400/800/1200/1600) with `srcset`; lazy-loading below the fold; explicit `width`/`height` to prevent layout shift |
| Fonts | Self-hosted, Latin subset, `font-display: swap`, preload of the two most-used files |
| API | Indexed filters, `selectinload` for related rows, pagination, `price_from` cache for price sorting, HTTP caching on public catalogue GETs: listings/home `public, max-age=60`; product detail and reviews `no-cache` (stock, price and newly published reviews must be current) |
| Database | `EXPLAIN ANALYZE` of the listing and search queries with 1,000+ products (`scripts/perf_catalogue.py` on a `*_perf` database) |
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

Lighthouse and API timings: see the 2026-10-15 entries below.

### 2026-10-15 — Lighthouse, production build behind the production web server
Environment: `npm run build` served by Caddy 2.10.2 with `deploy/Caddyfile` (CSP, compression,
caching) on `localhost:5190`, local API and PostgreSQL 17, sample catalogue. Lighthouse 12.8.2,
headless Chromium; "mobile" = Lighthouse default (Moto G-class device, 4× CPU slowdown, slow 4G),
"desktop" = `--preset=desktop`. Machine benchmark index ≈ 2,000. Local network, so real-world
latency to a server in India is **not** included.

First run (before fixes):
| Page | Mobile perf | Desktop perf | CLS (desktop / mobile) | Cause |
|------|-----------:|-------------:|------------------------|-------|
| Home | 48* | 84 | 0.296 / 0.041 | announcement bar appeared after the settings request and pushed the page down |
| Rings listing | 60 | 79 | 0.461 / 0.963 | footer visible while loading, then pushed down by the product grid |
| Om Pendant | 83 | 77 | 0.601 / 0.040 | same as above |
\* the very first run was noisy (TBT 1,970 ms); repeated runs gave 76–77.

Fixes: the announcement bar's space is reserved while settings load; `<main>` is at least one
screen tall so the footer stays below the fold while a page loads; product details now revalidate
on every request (`Cache-Control: no-cache`) so stock and price are never up to 60 s stale.

After the fixes (`ALLOW_SEARCH_INDEXING=true` so the SEO score reflects the live configuration):
| Page | Mobile perf / LCP / TBT / CLS | Desktop perf / LCP / CLS | Accessibility | Best practices | SEO |
|------|------------------------------|--------------------------|--------------:|---------------:|----:|
| Home | 79 / 3.5 s / 290 ms / 0 | 94 / 0.8 s / 0.14 | 100 | 100 | 100 |
| Rings listing | 79 / 3.7 s / 220 ms / 0.039 | 99 / 0.7 s / 0.003 | 100 | 100 | 100 |
| Om Pendant | 79 / 3.8 s / 210 ms / 0 | 99 / 0.8 s / 0.003 | 100 | 100 | 100 |
| About | 83 / 3.7 s / 70 ms / 0.007 | 99 / 0.8 s / 0.003 | 100 | 100 | 100 |
| Search "ring" | 83 / 3.6 s / 110 ms / 0.028 | 99 / 0.8 s / 0.054 | 100 | 100 | 69 (`noindex` on purpose) |

Remaining gap: mobile LCP ≈ 3.5–3.8 s under simulated slow 4G (target for "good" is ≤ 2.5 s). The
SPA must download and run its JavaScript before it can request the hero/product image. The main
bundle is lean (298 kB raw, 93 kB gzip; two thirds is React itself — source-map-explorer), so the
next step is pre-rendering the public pages (KNOWN_LIMITATIONS), not trimming code. The desktop
home CLS (0.14) comes from the hero section settling after its image loads; the image has explicit
dimensions, so this needs a closer look once real photography replaces the illustrations.

### 2026-10-15 — Catalogue API with 1,000 products
`scripts/perf_catalogue.py` on a separate `anvika_perf` database (seed + 969 copies of the sample
products, `ANALYZE`d). In-process requests (FastAPI TestClient → local PostgreSQL 17), 60 requests
per endpoint after a warm-up. This measures the application and database work, not the network,
and not Supabase's production tier (re-run there before launch).

| Endpoint | p50 | p95 | max |
|----------|----:|----:|----:|
| Listing (default) | 48.6 ms | 62.6 ms | 91.1 ms |
| Listing, category + price sort | 48.7 ms | 57.4 ms | 68.4 ms |
| Listing, filters | 43.1 ms | 56.1 ms | 61.9 ms |
| Search "gold ring" | 56.5 ms | 70.5 ms | 140.4 ms |
| Facets (category) | 23.7 ms | 30.8 ms | 35.4 ms |
| Facets (search) | 54.3 ms | 75.4 ms | 75.8 ms |
| Product detail | 23.9 ms | 31.5 ms | 41.8 ms |
| Home | 44.0 ms | 55.1 ms | 64.6 ms |

Target "listing p95 < 300 ms with 1,000 products": met locally (62.6 ms). `EXPLAIN ANALYZE` of
the default listing page: sequential scan of 1,000 rows + top-N heapsort, 1.1 ms execution — the
database is not the bottleneck at this size; most of the time is building priced cards in Python.
Indexes on `(status, category_id)` and `published_at` take over as the catalogue grows.

### 2026-10-15 — Bundle
Storefront initial JS 93 kB gzip (target < 200 kB ✅). Admin, account, checkout, content and
after-sales screens are separate chunks.

### 2026-10-16 — Home page with the scroll-scrubbed 3D necklace hero (ADR-0010)
Same environment as 2026-10-15 (production build behind Caddy, Lighthouse 12.8.2, local API).
Bundles: storefront initial JS 93.7 kB gzip (unchanged — the hero frame and copy only); 3D chunk
`NecklaceStage` 286 kB gzip (1.03 MB raw: three.js 570 kB, React Three Fiber 162 kB, GSAP 111 kB
raw). R3F v9 imports all of three.js (`import * as THREE` + `extend(THREE)`), so it can't be
tree-shaken while R3F is used.

Iterations (home page, desktop / mobile):
| Version | Desktop perf, LCP, TBT | Mobile perf, LCP, TBT | Finding |
|---------|------------------------|-----------------------|---------|
| Physically based materials + generated studio environment (PMREM), chunk loaded at render | 59–61, 1.3–1.4 s, 3.8 s | 34–36, 5.9–6.2 s, 10–11 s | One ≈3.7 s "unattributable" task = WebGL work (environment cube map + PBR shader compile in software GL) |
| Matcap materials (lighting baked into a 2D-canvas texture), no environment, no lights, DPR ≤ 1.5 | 79–94, 1.1–1.2 s, 150–400 ms | 43–44, 5.6 s, 1.5–1.6 s | Mobile LCP: the 286 kB chunk competed with the headline font on slow 4G |
| + 3D chunk loaded only after `load` and an idle moment (final) | **76–90, 0.7–0.8 s, 250–590 ms** | **60–70, 3.2–3.4 s, 0.8–1.4 s** | Remaining TBT = evaluating three.js + R3F on a 4× slowed CPU |

All runs: accessibility 100, best practices 100, CLS ≤ 0.032. For comparison, the home page
before the 3D hero (2026-10-15): desktop 94–99, mobile 77–79, LCP 3.5 s on mobile (the hero
illustration was the LCP element; now the headline is). Lighthouse renders WebGL in software, so
real GPUs do the drawing part faster; script evaluation cost is real on low-end phones.
Options if mobile scores matter more than the effect: skip the 3D hero on low-end devices or
`Save-Data`, or replace R3F with plain three.js (≈100–150 kB gzip less) — the latter conflicts
with the requirement to use React Three Fiber.
