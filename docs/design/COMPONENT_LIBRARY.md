# Component Library

Location: `frontend/src/components/`. Primitives in `ui/` are styled with design tokens and built on
Radix (`radix-ui`) where interaction semantics are non-trivial (dialogs, menus, popovers, tabs,
accordions, selects). Each primitive documents its props in TSDoc and has at least one test when
it contains behaviour.

## Primitives (`components/ui/`)
| Component | Built on | Variants / notes |
|-----------|----------|------------------|
| `Button` | `<button>` / `asChild` (Radix Slot) | `primary` (ink bg), `secondary` (outline), `ghost`, `link`, `danger`; sizes `sm/md/lg`; `loading` state keeps width, sets `aria-busy`, and disables |
| `IconButton` | Button | requires `label` (becomes `aria-label`) |
| `Input`, `Textarea` | native | used through `FormField`, which wires `id`, `<label>`, hint and error (`aria-describedby`, `aria-invalid`) |
| `Select` | native `<select>` | native for mobile usability (states list, sorting) |
| `Checkbox`, `RadioGroup` | Radix | shipping-method cards use RadioGroup |
| `QuantityStepper` | buttons + live region | min/max, announces changes |
| `Dialog`, `Sheet` (side drawer) | Radix Dialog | focus trap, Esc closes, returns focus |
| `ConfirmDialog` | Dialog | destructive confirmations ("Remove from cart?" is NOT confirmed — it is undoable; deleting an address is) |
| `DropdownMenu` | Radix | account menu, admin row actions |
| `Accordion` | Radix | product details sections, FAQ, mobile filters |
| `Tabs` | Radix | product info, admin order detail |
| `Badge` | span | `neutral`, `gold`, `success`, `warning`, `danger`; always contains text |
| `StatusPill` | Badge + icon | order/payment status (icon + text, never colour only) |
| `Skeleton` | div | shimmer disabled under reduced motion |
| `Spinner` | svg | `role="status"` + visually hidden label |
| `Toast` / `Toaster` | custom + `aria-live="polite"` | success/info/error |
| `Alert` | div `role="alert"` for errors, `status` for info | inline messages |
| `EmptyState` | — | icon, title, text, action |
| `ErrorState` | — | message + Retry button (calls `refetch`) |
| `Pagination` | nav | `aria-current="page"`, prev/next |
| `Price` | span | formats a money string with `Intl.NumberFormat('en-IN', {style:'currency',currency:'INR'})`; no arithmetic |
| `VisuallyHidden`, `SkipLink` | — | a11y helpers |

## Layout (`components/layout/`)
`AnnouncementBar`, `SiteHeader` (logo, search, account, wishlist, cart with count), `DesktopNav`,
`MobileNav` (Sheet), `SiteFooter`, `PageHeader` (eyebrow + title + description + breadcrumbs),
`Breadcrumbs`, `Container`, `Section`, `AdminLayout` (sidebar + top bar), `AccountLayout`.

## Commerce (`components/product`, `cart`, `checkout`, `account`)
| Component | Purpose |
|-----------|---------|
| `ProductCard` | image (4:5, lazy), name, purity · weight, price "from", stock hint, wishlist toggle |
| `ProductGrid` | responsive grid + skeletons |
| `FilterPanel` / `ActiveFilters` / `SortSelect` | URL-driven filters; mobile in a Sheet |
| `ProductGallery` | thumbnails, keyboard-navigable, zoom dialog |
| `VariantPicker` | radio group of sizes; shows unavailable sizes as disabled, with text |
| `PriceBreakdown` | renders the backend breakdown rows (metal, making, stones, discount, GST, total) |
| `StockStatus` | text + icon |
| `PincodeChecker` | form → serviceability + delivery range |
| `SpecTable` | definition list of product specifications |
| `WishlistButton` | toggle with `aria-pressed` |
| `CartLine`, `CartSummary`, `CouponForm`, `PriceChangeNotice` | cart |
| `CheckoutSteps`, `AddressForm`, `ShippingMethodPicker`, `OrderReview`, `PaymentButton`, `SimulatedPaymentDialog` | checkout |
| `OrderTimeline`, `OrderSummaryCard`, `AddressCard` | account |

## Admin (`components/admin/`)
`DataTable` (sortable headers, pagination, empty/loading/error states), `StatCard`,
`FormSection`, `ImageUploader` (drag-reorder with keyboard alternative: move up/down buttons),
`AuditDiff`, `ConfirmAction`.

## Rules
1. Primitives accept `className` and merge it with `cn()` (clsx + tailwind-merge).
2. No component fetches data except page components and `*Container` components; presentational
   components receive props.
3. All interactive components are keyboard operable and have a visible focus ring
   (`focus-visible:outline-2 outline-focus outline-offset-2`).
