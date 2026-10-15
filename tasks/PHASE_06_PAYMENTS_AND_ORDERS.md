# Phase 6 — Checkout, Payments and Orders  ✅ complete (2026-10-15)

Goal: a tested sandbox purchase workflow, safe under failures and duplicates.

## Tasks
- [x] Models + migration: orders, order_items, order_events, inventory_reservations, payment_attempts,
      payment_events, refunds, shipments (`return_requests` → Phase 7 with the returns workflow)
- [x] Inventory service: reserve / commit / release / restock with row locks + ledger
- [x] Optional checkout block when the gold rate is stale (`block_checkout_when_rate_stale`)
- [x] Checkout service: quote; order creation (idempotency key, pending-order reuse, expected_total,
      stock, coupon lock, snapshots); guest access token
- [x] Payment gateway interface; Razorpay REST client (create order, fetch payment, refund); simulator
- [x] `mark_order_paid` idempotent transition; verify endpoint; retry endpoint; failure report
- [x] Webhook endpoint: raw-body HMAC, event-id dedupe, handlers
- [x] Order state machine + events; customer cancel; refund records
- [x] Background jobs: expiry + reconciliation, email dispatch, price cache refresh; `run-jobs`,
      `reconcile-payments` CLI
- [x] Email templates: order confirmation, cancelled (status / shipment / refund emails → Phase 7,
      where admins trigger those changes)
- [x] Frontend: checkout (contact, address w/ saved addresses, shipping, review, terms, pay), Razorpay
      Checkout.js loader, simulated payment dialog, failure/retry UI, order confirmation, account orders
      list/detail with timeline, cancel action
- [x] Tests: checkout, payments, webhooks, concurrency (threads), expiry, late capture, cancellation; e2e J3/J4

## Acceptance
J3, J4, J5, J6, J11 pass; payment status only from verified events.

Notes:
- J5 (duplicate webhooks) and J6 (unavailable stock) are covered by API tests
  (`test_webhook_capture_confirms_once_and_ignores_duplicates`, `test_last_piece_goes_to_the_first_buyer`,
  `test_only_one_of_two_simultaneous_checkouts_gets_the_last_piece`); J3, J4 and J11 also end to end.
- Real Razorpay test-mode keys have NOT been used yet (none provided). The Razorpay client is tested
  against a mocked Razorpay API (`test_full_checkout_against_mocked_razorpay`); a sandbox run with
  real test keys is on the Phase 8 checklist.
- Refunds are recorded as `requested`; executing them with Razorpay is an admin action (Phase 7).
- Defects found and fixed while testing: simulated payment ids exceeded the 128-character column;
  Decimal values in JSONB snapshots; email sent twice in tests because of a read transaction left
  open before after-response work; e2e label clash with the footer newsletter field.
