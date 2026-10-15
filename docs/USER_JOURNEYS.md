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
* Tests: `e2e/browse.spec.ts`, `e2e/cart.spec.ts`; API `tests/api/test_catalogue.py`, `test_cart.py`.

## J2 — Register and manage addresses
`/register` → account created → `/account` → **Addresses** → add a default shipping address →
edit → delete.
* Tests: `e2e/account.spec.ts`; API `tests/api/test_auth.py`, `test_account.py::test_address_crud_and_defaults`.

## J3 — Guest checkout with test payment
Cart → `/checkout` → contact + address (PIN validated) → shipping method → review (itemised totals,
terms checkbox) → **Pay** → payment pop-up (Razorpay test mode or simulator) → backend verifies →
`/order-confirmation/{ref}` (accessible through the private guest token) → confirmation email in the
outbox.
* Tests: `e2e/checkout.spec.ts`; API `tests/api/test_checkout.py`, `test_payments.py`.

## J4 — Payment failure and retry
Pop-up returns failure (or is dismissed) → order stays pending and the customer sees "Payment not
completed" with **Try again** → retry succeeds → only one order exists.
* Tests: `e2e/checkout.spec.ts` (failure case); API `test_payments.py::test_failed_payment_can_be_retried`.

## J5 — Duplicate webhooks
Razorpay sends `payment.captured` twice, and the verify endpoint also runs → order confirmed once,
stock decremented once, one confirmation email.
* Tests: API `test_payments.py::test_webhook_capture_confirms_once_and_ignores_duplicates`, `test_verifying_twice_is_harmless`.

## J6 — Unavailable stock
Two customers race for the last piece → one order succeeds, the other gets `OUT_OF_STOCK` with a
clear message, and the cart shows the item as unavailable.
* Tests: API `test_inventory_concurrency.py::test_only_one_of_two_simultaneous_checkouts_gets_the_last_piece`
  (two real connections), `test_checkout.py::test_last_piece_goes_to_the_first_buyer`; e2e
  `journeys.spec.ts` (sold-out piece blocked in cart and checkout).

## J7 — Gold rate change
Customer adds a 22K product → admin publishes a higher 22K rate → the customer's cart shows "Price
updated" and checkout requires acceptance → placing an order with the stale `expected_total`
returns `PRICE_CHANGED`.
* Tests: API `test_checkout.py::test_price_increase_must_be_accepted_before_checkout`,
  `test_order_snapshot_does_not_change_when_gold_rate_changes`; e2e `journeys.spec.ts` (J7).

## J8 — Admin creates a product, customer sees it
Admin → Products → New → fills details, variants, stock, images → Publish → product appears in its
collection and in search.
* Tests: e2e `admin.spec.ts` (create → photo → publish → visible); API `test_admin_catalogue.py`.

## J9 — Admin changes inventory
Admin sets stock to 0 → product page shows Out of stock → add-to-cart disabled, and checkout of an
existing cart line is rejected.
* Tests: API `test_admin_ops.py::test_stock_adjustments_are_ledgered_and_audited`,
  `test_cart.py::test_stock_problems_block_checkout`; e2e `admin.spec.ts` (adjustment),
  `journeys.spec.ts` (sold out → product page, cart and checkout blocked).

## J10 — Access control
Customer A requests customer B's order → 404. A customer calls `/api/v1/admin/*` → 403. A guest with
only the order reference → 404.
* Tests: API `test_account.py::test_customers_cannot_touch_each_others_addresses`,
  `test_checkout.py::test_guest_order_needs_its_access_token`, `test_permissions.py`, admin
  permission tests; e2e `admin.spec.ts` (customers cannot use the admin).

## J11 — Cancel an eligible order
A customer cancels a confirmed (paid, not yet processing) order → status cancelled, stock restored,
refund record created → admin processes the refund.
* Tests: API `test_payments.py::test_cancel_paid_order_restocks_and_requests_refund`,
  `test_admin_ops.py::test_admin_cancels_paid_order_with_full_refund`; e2e `checkout.spec.ts`,
  `admin.spec.ts` (cancel + refund).

## J12 — Keyboard and responsive
Complete J1 + J3 with keyboard only; the layout works at 375 px, 768 px and 1280 px.
* Tests: e2e `accessibility.spec.ts` (keyboard flow + axe), `journeys.spec.ts` (keyboard-only
  product → cart → checkout; 375/768/1280 px without sideways scrolling), mobile project.
  A manual keyboard pass of the full checkout by a person is still on the production checklist.
