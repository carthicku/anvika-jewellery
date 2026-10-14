# Phase 6 — Checkout, Payments and Orders

Goal: a tested sandbox purchase workflow, safe under failures and duplicates.

## Tasks
- [ ] Models + migration: orders, order_items, order_events, inventory_reservations, payment_attempts,
      payment_events, refunds, shipments, return_requests
- [ ] Inventory service: reserve / commit / release / restock with row locks + ledger
- [ ] Checkout service: quote; order creation (idempotency key, pending-order reuse, expected_total,
      stock, coupon lock, snapshots); guest access token
- [ ] Payment gateway interface; Razorpay REST client (create order, fetch payment, refund); simulator
- [ ] `mark_order_paid` idempotent transition; verify endpoint; retry endpoint
- [ ] Webhook endpoint: raw-body HMAC, event-id dedupe, handlers
- [ ] Order state machine + events; customer cancel; refund records
- [ ] Background jobs: expiry + reconciliation, email dispatch, price cache refresh; `run-jobs`,
      `reconcile-payments` CLI
- [ ] Email templates: order confirmation, cancelled, status, shipment, refund
- [ ] Frontend: checkout (contact, address w/ saved addresses, shipping, review, terms, pay), Razorpay
      Checkout.js loader, simulated payment dialog, failure/retry UI, order confirmation, account orders
      list/detail with timeline, cancel action
- [ ] Tests: checkout, payments, webhooks, concurrency (threads), expiry, late capture, cancellation; e2e J3/J4

## Acceptance
J3, J4, J5, J6, J11 pass; payment status only from verified events.
