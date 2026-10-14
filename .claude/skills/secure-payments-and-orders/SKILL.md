---
name: secure-payments-and-orders
description: Use when working on checkout, order creation, Razorpay integration, payment verification, webhooks, retries, refunds, cancellations, order status transitions, or the payment simulator. Enforces signature verification, idempotency, correct state transitions and never faking payment success.
---

# Secure payments and orders

Specs: `docs/architecture/PAYMENT_FLOW.md`, `docs/architecture/INVENTORY_AND_ORDERS.md`,
ADR-0005. Code: `backend/app/services/checkout.py`, `orders.py`, `payments/`,
`api/v1/routes/payments.py`, `webhooks.py`.

## Golden rules
1. **An order becomes paid only via `payments.service.mark_order_paid`**, called after (a) a valid
   checkout signature computed with the **stored** provider order id **and** a fetched payment with
   `status == captured`, matching amount (paise), currency and order id; or (b) a verified webhook;
   or (c) reconciliation. Nothing else may set `payment_status = paid`. Admins cannot.
2. `mark_order_paid` locks the order row and is idempotent. A second call is a no-op returning the
   current state.
3. Webhooks: verify `X-Razorpay-Signature` = HMAC-SHA256(raw body, webhook secret) **before** parsing;
   dedupe by `x-razorpay-event-id` (unique constraint); store and acknowledge unknown events.
4. Amount authority: the Razorpay order amount = `orders.grand_total` × 100 from the DB.
5. Duplicate submissions: `Idempotency-Key` header (unique on orders) + reuse of the pending order.
6. Stock reservation happens in the same transaction as order creation. Commit on payment. Release on
   expiry/cancel. A late capture is re-reserved or sent to `payment_review`.
7. Fulfilment (`processing`, `shipped`) requires `payment_status == paid`.
8. Transitions only through `ALLOWED_TRANSITIONS`. Each writes an `order_events` row (+ audit log for
   admins).
9. Secrets (`RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`) stay on the backend; never log them,
   never return them. The browser gets only the key id, provider order id, amount and prefill.
10. **Never fake payment success.** The simulator exists only for dev/test, is rejected when
    `APP_ENV=production`, uses the same verification path, and is labelled in the UI.
11. Never store card numbers, CVV, UPI PINs or bank credentials.

## Review checklist
- [ ] Can a browser-supplied value change the amount charged or the paid state? (must be no)
- [ ] What happens if this request is sent twice? Concurrently?
- [ ] What happens if Razorpay times out after creating the order? After capturing?
- [ ] What happens if the webhook arrives before/after the verify call?
- [ ] Are stock, coupon redemptions and emails each affected exactly once?
- [ ] Are failures visible to the customer (retry) and the admin (needs attention)?

## Required tests
Forged signature, amount mismatch, authorized-not-captured, duplicate verify, duplicate webhook,
webhook before verify, retry after failure (single order), expiry releases stock, late capture
(with and without stock), cancellation restock + refund record, fulfilment blocked when unpaid.
