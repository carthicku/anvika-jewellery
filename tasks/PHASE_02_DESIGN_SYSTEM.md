# Phase 2 — Design System and Storefront Shell  ✅ complete (2026-10-14)

Goal: a cohesive, interactive, responsive storefront built from reusable components.

> Deviation from the brief (documented): instead of building pages on temporary hard-coded sample
> data and rewiring them later, Phase 3's catalogue API is built immediately after the component
> library, and pages are wired to the real API from the start. Sample content comes from the seed
> data. This avoids throwaway code and any risk of fixtures leaking into production.

## Tasks
- [x] Design tokens in `src/styles/index.css` (`@theme`) matching DESIGN_SYSTEM.md
- [x] Fonts self-hosted (Cormorant Garamond 500/600, Inter variable) with fallbacks
- [x] Primitives built: Button, IconButton, Input/Textarea/Select/FormField, Checkbox, Dialog, Sheet,
      Accordion, Badge, Skeleton, Spinner, Toaster, Alert, EmptyState, ErrorState, Pagination, Price,
      skip link (sr-only utility instead of separate VisuallyHidden/SkipLink components)
- [ ] Deferred to the phases that need them: QuantityStepper (Phase 5), RadioGroup, ConfirmDialog,
      DropdownMenu, Tabs, StatusPill (Phases 4–7)
- [x] Layout: AnnouncementBar, SiteHeader (desktop nav + mobile menu sheet + search dialog),
      SiteFooter (+ newsletter), PageHeader, Breadcrumbs, Container, PageMeta. AccountLayout → Phase 4
- [x] Placeholder jewellery illustrations (SVG line art) for sample products/categories/hero
- [x] Home page sections (hero, categories, new arrivals, bestsellers, collections, story, trust/services,
      care guide teaser, newsletter, service info)
- [x] Product components (wishlist is guest-only until Phase 4): ProductCard, ProductGrid, FilterPanel, ActiveFilters, SortSelect, ProductGallery
      (+ zoom dialog), VariantPicker, PriceBreakdown, StockStatus, SpecTable, WishlistButton, PincodeChecker
- [x] Pages: collections index, collection/category listing, search, product detail, supporting pages,
      404 — wired to the Phase 3 API
- [x] Recently viewed (localStorage, try/catch guarded)
- [x] Focus management on route change, skip link, document titles/meta
- [x] Component tests for interactive pieces
- [x] Manual responsive check at 375 / 768 / 1280 (recorded)

## Acceptance
Every interactive element does something real; no `href="#"`; loading/empty/error states exist for
every data view; axe has no serious violations on home/listing/product.

Verification: 21 Vitest tests and 25 Playwright runs (desktop + mobile), including axe scans of 7
pages with no serious/critical violations, plus manual screenshot review at 1440 px and 390 px. Two
accessibility bugs were found and fixed: focus jumped into <main> on first load (StrictMode double
effect), and focus was lost after closing dialogs opened without a Radix trigger.
