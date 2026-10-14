# Phase 2 — Design System and Storefront Shell

Goal: a cohesive, interactive, responsive storefront built from reusable components.

> Deviation from the brief (documented): instead of building pages on temporary hard-coded sample
> data and rewiring them later, Phase 3's catalogue API is built immediately after the component
> library, and pages are wired to the real API from the start. Sample content comes from the seed
> data. This avoids throwaway code and any risk of fixtures leaking into production.

## Tasks
- [ ] Design tokens in `src/styles/index.css` (`@theme`) matching DESIGN_SYSTEM.md
- [ ] Fonts self-hosted (Cormorant Garamond 500/600, Inter variable) with fallbacks
- [ ] Primitives: Button, IconButton, Input/Textarea/FormField, Select, Checkbox, RadioGroup, QuantityStepper,
      Dialog, Sheet, ConfirmDialog, DropdownMenu, Accordion, Tabs, Badge, StatusPill, Skeleton, Spinner,
      Toaster, Alert, EmptyState, ErrorState, Pagination, Price, VisuallyHidden, SkipLink
- [ ] Layout: AnnouncementBar, SiteHeader, DesktopNav, MobileNav, SiteFooter, PageHeader, Breadcrumbs,
      Container, Section, AccountLayout
- [ ] Placeholder jewellery illustrations (SVG line art) for sample products/categories/hero
- [ ] Home page sections (hero, categories, new arrivals, bestsellers, collections, story, trust/services,
      care guide teaser, newsletter, service info)
- [ ] Product components: ProductCard, ProductGrid, FilterPanel, ActiveFilters, SortSelect, ProductGallery
      (+ zoom dialog), VariantPicker, PriceBreakdown, StockStatus, SpecTable, WishlistButton, PincodeChecker
- [ ] Pages: collections index, collection/category listing, search, product detail, supporting pages,
      404 — wired to the Phase 3 API
- [ ] Recently viewed (localStorage, try/catch guarded)
- [ ] Focus management on route change, skip link, document titles/meta
- [ ] Component tests for interactive pieces
- [ ] Manual responsive check at 375 / 768 / 1280 (recorded)

## Acceptance
Every interactive element does something real; no `href="#"`; loading/empty/error states exist for
every data view; axe has no serious violations on home/listing/product.
