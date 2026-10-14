# User Journeys

Each journey lists the steps, what the system must do, and the automated test that covers it.
E2E specs live in `frontend/e2e/`; API tests live in `backend/tests/`.

## J1 — Discover and add to cart (guest, mobile)
1. Lands on `/` → sees hero, categories, new arrivals.
2. Taps **Rings** → `/collections/rings`; filters 22K, sorts by price low→high. URL updates
   (`?purity=22K&sort=price_asc`) so the view can be shared.
3. Opens a product → gallery, purity, weights, price breakdown, stock status, delivery check by PIN.
4. Selects a ring size → price and stock update for that variant.
5. **Add to cart** → cart count updates and an announcement is read by screen readers.
6. In `/cart` changes the quantity → totals recalculated by the backend.
* Tests: `e2e/browse-and-cart.spec.ts`; API `tests/api/test_catalogue.py`, `test_cart.py`.

## J2 — Register and manage addresses
`/register` → account created → `/account` → **Addresses** → add a default shipping address →
edit → delete.
* Tests: `e2e/account.spec.ts`; API `tests/api/test_auth.py`, `test_addresses.py`.

## J3 — Guest checkout with test payment
Cart → `/checkout` → contact + address (PIN validated) → shipping method → review (itemised totals,
terms checkbox) → **Pay** → payment pop-up (Razorpay test mode or simulator) → backend verifies →
`/order-confirmation/{ref}` (accessible through the private guest token) → confirmation email in the
outbox.
* Tests: `e2e/checkout.spec.ts`; API `tests/api/test_checkout.py`, `test_payments.py`.

## J4 — Payment failure and retry
Pop-up returns failure (or is dismissed) → order stays pending and the customer sees "Payment not
completed" with **Try again** → retry succeeds → only one order exists.
* Tests: `e2e/checkout.spec.ts` (failure case); API `test_payments.py::test_retry_after_failure`.

## J5 — Duplicate webhooks
Razorpay sends `payment.captured` twice, and the verify endpoint also runs → order confirmed once,
stock decremented once, one confirmation email.
* Tests: API `test_webhooks.py::test_duplicate_events_are_idempotent`.

## J6 — Unavailable stock
Two customers race for the last piece → one order succeeds, the other gets `OUT_OF_STOCK` with a
clear message, and the cart shows the item as unavailable.
* Tests: API `test_inventory.py::test_concurrent_reservations_never_oversell` (threads), e2e
  out-of-stock message.

## J7 — Gold rate change
Customer adds a 22K product → admin publishes a higher 22K rate → the customer's cart shows "Price
updated" and checkout requires acceptance → placing an order with the stale `expected_total`
returns `PRICE_CHANGED`.
* Tests: API `test_pricing_changes.py`; e2e `price-change.spec.ts`.

## J8 — Admin creates a product, customer sees it
Admin → Products → New → fills details, variants, stock, images → Publish → product appears in its
collection and in search.
* Tests: e2e `admin-product.spec.ts`; API `test_admin_products.py`.

## J9 — Admin changes inventory
Admin sets stock to 0 → product page shows Out of stock → add-to-cart disabled, and checkout of an
existing cart line is rejected.
* Tests: API `test_admin_inventory.py`; e2e `admin-inventory.spec.ts`.

## J10 — Access control
Customer A requests customer B's order → 404. A customer calls `/api/v1/admin/*` → 403. A guest with
only the order reference → 404.
* Tests: API `test_access_control.py`.

## J11 — Cancel an eligible order
A customer cancels a confirmed (paid, not yet processing) order → status cancelled, stock restored,
refund record created → admin processes the refund.
* Tests: API `test_cancellation.py`.

## J12 — Keyboard and responsive
Complete J1 + J3 with keyboard only; the layout works at 375 px, 768 px and 1280 px.
* Tests: e2e `accessibility.spec.ts` (keyboard flow + axe checks), responsive projects in the
  Playwright config.
