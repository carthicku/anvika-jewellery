---
name: premium-ui-ux
description: Use when designing, building or reviewing any visible page or component of the jewellery storefront or admin — layout, typography, colour, imagery, spacing, interaction states, responsiveness or accessibility. Enforces the premium minimal design system and prevents generic template-looking UI.
---

# Premium jewellery UI/UX

## Read first
`docs/design/DESIGN_SYSTEM.md` (tokens and rules), `docs/design/COMPONENT_LIBRARY.md`,
`docs/design/RESPONSIVE_GUIDELINES.md`, `docs/design/ACCESSIBILITY.md`.

## Principles
1. **The jewellery is the hero.** Large 4:5 images on `surface-muted`, generous whitespace, few
   elements per screen.
2. **Restraint is luxury.** Ivory background, charcoal text, gold only as a hairline accent
   (≤ ~5% of a screen). No gradients, neon, glassmorphism, giant pills, or icon clutter.
3. **Typography carries elegance.** Cormorant Garamond for display headings only (≥ 18 px);
   Inter for everything else; prices `tabular-nums`; eyebrows uppercase with wide tracking.
4. **Transparency builds trust.** Show purity, weight and the itemised price breakdown plainly.
   Never invent claims, ratings, certifications or scarcity.
5. **Quiet motion.** 150–250 ms opacity/transform; nothing auto-plays; respect reduced motion.

## Review checklist
- [ ] Uses token utilities (`bg-ivory`, `text-ink`, `border-line`, `outline-focus`), with no raw hex.
- [ ] Clear hierarchy: one H1, eyebrow → heading → supporting text; consistent section rhythm
      (`py-16` / `lg:py-24`).
- [ ] Aligned to the grid and `Container` widths; consistent card image ratios.
- [ ] All states designed: loading (skeleton matching final layout), empty (helpful next step),
      error (message + retry), success, disabled, focus, hover, pressed.
- [ ] Works at 320/375, 768, 1280 px; touch targets ≥ 44 px; no horizontal scroll.
- [ ] Every interactive element performs a real action (no `href="#"`, no dead buttons).
- [ ] Accessible names, labels, focus ring, contrast (see the measured ratios in DESIGN_SYSTEM.md).
- [ ] Copy is calm and precise. Placeholders for business facts are clearly marked
      `[To be configured]`.
- [ ] Would this look at home next to a respected fine-jewellery brand? If it looks like a generic
      marketplace template, simplify: remove borders, add whitespace, enlarge imagery, reduce colours.
