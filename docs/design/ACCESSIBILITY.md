# Accessibility

Target: **WCAG 2.2 AA** where practical. Findings are recorded in
[`docs/quality/TEST_RESULTS.md`](../quality/TEST_RESULTS.md).

## Checklist (applied to every page and component)
### Structure
- [ ] One `<h1>` per page; headings are not skipped.
- [ ] Landmarks: `header`, `nav` (labelled when more than one), `main#main`, `footer`.
- [ ] "Skip to content" link is the first focusable element.
- [ ] `<html lang="en-IN">`; page `<title>` is unique and descriptive.

### Keyboard & focus
- [ ] Everything works with Tab / Shift+Tab / Enter / Space / Esc / arrow keys (radio groups, menus,
      gallery thumbnails).
- [ ] Focus ring always visible (`:focus-visible` 2 px `focus` colour outline + offset, ≥ 3:1), never removed.
- [ ] Dialogs trap focus and return it to the trigger; Esc closes them.
- [ ] After route changes, focus moves to the page `<h1>` (or `main`) and the new title is announced.
- [ ] WCAG 2.2: focused elements are not hidden behind sticky headers/bars (`scroll-margin-top`);
      targets are at least 24 × 24 px (we use 44).

### Forms
- [ ] Every input has a visible `<label>`; placeholder is never the label.
- [ ] Errors are text, linked with `aria-describedby`, and the field gets `aria-invalid="true"`;
      on submit, focus moves to the first invalid field; a summary is announced.
- [ ] `autocomplete` attributes are set (name, email, tel, address-line1, postal-code, …).
- [ ] WCAG 2.2 "Redundant entry": billing address can be "same as shipping"; saved addresses are
      offered to signed-in users.
- [ ] WCAG 2.2 "Accessible authentication": password fields allow paste and password managers; no
      cognitive tests (no CAPTCHA puzzles).

### Content
- [ ] Text contrast ≥ 4.5:1 (≥ 3:1 for large text); UI component boundaries ≥ 3:1.
- [ ] Status never relies on colour alone.
- [ ] Images have meaningful `alt`; decorative images use `alt=""`.
- [ ] Prices are read correctly ("₹32,301" rather than characters); strike-through prices include
      visually hidden "Original price" text.

### Dynamic updates
- [ ] Cart count changes and "Added to cart" are announced via a polite live region.
- [ ] Loading states use `aria-busy` and/or `role="status"`.
- [ ] Price-change notices use `role="alert"`.

### Motion
- [ ] `prefers-reduced-motion` respected; no auto-playing carousels; nothing flashes.

## Testing
* Automated: `@axe-core/playwright` scan on key pages (home, listing, product, cart, checkout,
  login, account, admin dashboard) — fails the test on serious/critical violations.
* Component tests use Testing Library queries by role/label (which also checks accessible names).
* Manual: keyboard-only pass of journeys J1 and J3; screen reader spot check (NVDA on Windows) of
  product page, cart and checkout — results recorded in TEST_RESULTS.md.
