# Design System

The look: a quiet, well-lit jewellery showroom. Warm ivory space, charcoal type, a thin line of
champagne gold, and the jewellery itself as the hero. Restraint is the luxury.

Tokens are implemented in `frontend/src/styles/index.css` (Tailwind v4 `@theme`). **Use the token
utilities (`bg-ivory`, `text-ink`, `border-line`…), never raw hex values in components.**

## 1. Colour

| Token | Hex | Use | Contrast note |
|-------|-----|-----|---------------|
| `ivory` | `#FAF7F2` | Page background | — |
| `surface` | `#FFFFFF` | Cards, inputs, dialogs | — |
| `surface-muted` | `#F3EEE6` | Image wells, subtle sections | — |
| `ink` | `#1F1D1A` | Primary text, primary buttons | 15.7:1 on ivory |
| `ink-muted` | `#5C574F` | Secondary text | 6.7:1 on ivory |
| `ink-subtle` | `#6F695F` | Captions, placeholders | 5.1:1 on ivory, 4.7:1 on surface-muted |
| `line` | `#E6DFD3` | Hairline dividers (decorative only) | decorative |
| `line-strong` | `#8C8273` | Input, checkbox and select borders | 3.5:1 on ivory, 3.8:1 on white (WCAG 1.4.11) |
| `gold` | `#B08D57` | Decorative accents: thin rules, eyebrow dashes, active underline | 2.9:1 — **decorative only, never text or focus** |
| `focus` | `#9C7A45` | Focus ring (2 px) | 3.7:1 on ivory, 3.4:1 on surface-muted |
| `gold-deep` | `#7E5F2F` | Gold-tinted text and links when needed | 5.5:1 on ivory |
| `gold-soft` | `#EFE6D6` | Selected chips, highlights | — |
| `noir` | `#1A1815` | Dark feature sections, footer | — |
| `noir-ink` | `#F4EFE7` | Text on noir | 15.5:1 |
| `success` | `#2F6B4F` | In stock, paid | 5.9:1 on ivory |
| `warning` | `#8A5A12` | Low stock, pending | 5.5:1 |
| `danger` | `#A23B32` | Errors, out of stock | 6.1:1 |
| `info` | `#2E5A7A` | Notices | 6.9:1 |

Ratios were calculated with the WCAG 2.x relative-luminance formula on 2026-10-14.

Rules
* Gold is an accent, used in at most ~5% of any screen. No gold body text, no gold gradients.
* Status is never shown by colour alone. Always pair it with text and/or an icon
  (e.g. "● Paid" + label).
* Dark (`noir`) sections at most once per page (e.g. the brand story) plus the footer.

## 2. Typography

| Role | Font | Size (mobile → desktop) | Weight | Notes |
|------|------|-------------------------|--------|-------|
| Display XL (hero) | Cormorant Garamond | 40 → 64 px | 500 | `tracking-tight`, line-height 1.05 |
| H1 | Cormorant Garamond | 32 → 44 px | 500 | |
| H2 | Cormorant Garamond | 26 → 34 px | 500 | |
| H3 | Inter | 18 → 20 px | 500 | |
| Eyebrow / overline | Inter | 12 px | 500 | uppercase, `tracking-[0.18em]`, `ink-muted` |
| Body | Inter | 16 px | 400 | line-height 1.6 |
| Small | Inter | 14 px | 400 | |
| Price | Inter | 18–24 px | 500 | `tabular-nums` |

* Fonts are **self-hosted** through `@fontsource` packages (no third-party font requests, better
  privacy and CSP), `font-display: swap`, Latin subset only. Fallbacks: `Georgia, serif` for display
  and `system-ui, sans-serif` for body.
* Never use the display serif for form labels, prices, or text under 18 px.

## 3. Spacing and layout
* 4 px base scale (Tailwind default). Section vertical rhythm: `py-16` mobile, `py-24` desktop.
* Content width: `max-w-7xl` (1280 px) with `px-4 sm:px-6 lg:px-8` gutters. Long text: `max-w-prose`.
* Product grid: 2 columns < 640 px, 3 columns ≥ 1024 px, 4 columns ≥ 1280 px. Gap `gap-x-4
  gap-y-10` → `gap-x-6 gap-y-12`.

## 4. Shape and depth
| Token | Value | Use |
|-------|-------|-----|
| `radius-sm` | 2 px | Buttons, inputs, chips |
| `radius-md` | 4 px | Cards, dialogs |
| `radius-lg` | 8 px | Large media only |
| `shadow-soft` | `0 1px 2px rgb(31 29 26 / 0.04), 0 4px 16px rgb(31 29 26 / 0.04)` | Dropdowns, sticky bars |
| `shadow-lift` | `0 8px 30px rgb(31 29 26 / 0.08)` | Dialogs |

No large rounded "pill" cards, no glassmorphism.

## 5. Imagery
* Product images: **4:5 portrait** ratio for cards and gallery, `object-cover` on `surface-muted`.
  Category tiles: 1:1. Hero: 16:9 desktop / 4:5 mobile (art-directed).
* Placeholder illustrations (fine gold line drawings on ivory) are used for sample products and
  are labelled "Sample image" in the admin.
* Every image has meaningful `alt` text (product name + key attribute), or `alt=""` when purely
  decorative.

## 6. Motion
* Durations 150–250 ms, `ease-out`. Only opacity, transform and colour transitions.
* Image hover: slow 400 ms opacity cross-fade to the second image (desktop only).
* `prefers-reduced-motion: reduce` disables all non-essential transitions.
* **One exception, the home hero** (ADR-0010): on a `noir` background, scattered diamonds assemble
  into a gold necklace as the visitor scrolls. It is never autoplayed — every frame is set by the
  scroll position, so it stops when the visitor stops and reverses exactly when they scroll back.
  The section is pinned for 1.6 screens. With reduced motion it is a still of the finished piece.
  3D material colours approximate the tokens under studio light (gold `#c9a463` renders as the
  brand gold `--color-gold`).

## 7. Voice
Calm, precise, warm. "Crafted in 22K gold", not "AMAZING DEALS!!!". Prices are explained, never
hidden. No invented claims (certifications, ratings, "bestselling" without data).

## 8. Iconography
Lucide icons at 20 px, stroke 1.5, `currentColor`. Icons support labels; they rarely replace them
(the header icons have accessible names and tooltips).
