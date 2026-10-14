# Responsive Guidelines

Mobile first: write base styles for ~375 px, then add `sm:` (640), `md:` (768), `lg:` (1024),
`xl:` (1280) overrides.

| Element | Mobile (< 768) | Tablet (768–1023) | Desktop (≥ 1024) |
|---------|----------------|-------------------|------------------|
| Header | Logo centred, menu (left), search + cart icons (right); search opens a full-width sheet | same + account icon | Full nav row, inline search, account, wishlist, cart |
| Navigation | `MobileNav` sheet with categories, collections, account links | sheet | Horizontal nav with a simple dropdown for categories |
| Product grid | 2 columns | 3 | 3–4 |
| Filters | "Filter" button opens a Sheet; "Sort" native select; active filters as chips | same | Left sidebar (sticky) |
| Product page | Gallery (swipe, dots) → info → sticky bottom "Add to cart" bar | two columns | Gallery (thumbnails left) + sticky info column |
| Cart | Lines stacked; summary below; sticky checkout button | same | Lines left, summary right (sticky) |
| Checkout | Single column, order summary collapsible at top | same | Form left, summary right |
| Admin | Usable on tablets; on phones tables scroll horizontally inside their card and the sidebar becomes a sheet | sidebar collapsible | Fixed sidebar |

Rules
* Touch targets ≥ 44 × 44 px (icon buttons are `size-11`).
* No horizontal page scrolling at 320 px. Wide tables scroll inside their own container with a
  visible scroll hint.
* Inputs use the right `type`/`inputmode`/`autocomplete` (`tel`, `email`, `postal-code`,
  `inputmode="numeric"` for PIN) so mobile keyboards help the shopper.
* Font size of inputs ≥ 16 px (prevents iOS zoom).
* Sticky bars respect `env(safe-area-inset-bottom)`.
* Images use `srcset`/`sizes` (or width-specific URLs from the image service) so phones download
  small files.
* Playwright runs the key journeys on `Mobile Chrome (Pixel 7)` and `Desktop Chrome` projects.
