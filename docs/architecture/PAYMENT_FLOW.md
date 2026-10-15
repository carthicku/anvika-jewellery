# Payment Flow (Razorpay)

Decision record: [ADR-0005](ADR/0005-razorpay-rest-integration.md). Setup steps:
[PAYMENT_PROVIDER_SETUP.md](../operations/PAYMENT_PROVIDER_SETUP.md).
Facts verified against Razorpay's documentation on 2026-10-14 (Orders API, Checkout.js, signature
formula, `X-Razorpay-Signature`, `x-razorpay-event-id`).

## 1. Happy path

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant API as FastAPI
    participant DB as PostgreSQL
    participant R as Razorpay
    B->>API: POST /checkout/quote (address, shipping method)
    API->>DB: load cart, rates, tax, stock
    API-->>B: breakdown + grand_total (no side effects)
    B->>API: POST /checkout/orders (Idempotency-Key, expected_total, terms_accepted)
    API->>DB: BEGIN; lock inventory rows; recalc price; check expected_total;<br/>insert order (pending_payment) + items + reservations; COMMIT
    API->>R: POST /v1/orders {amount (paise), currency INR, receipt=order ref}
    R-->>API: razorpay order_id
    API->>DB: insert payment_attempt (created)
    API-->>B: {order reference, key_id, razorpay_order_id, amount, prefill}
    B->>R: Checkout.js pop-up, customer pays
    R-->>B: handler(razorpay_payment_id, razorpay_order_id, razorpay_signature)
    B->>API: POST /payments/verify {…3 values…}
    API->>API: HMAC_SHA256(stored_order_id|payment_id, key_secret) == signature?
    API->>R: GET /v1/payments/{payment_id}
    R-->>API: status=captured, amount, currency, order_id
    API->>DB: BEGIN; lock order; if not already paid → commit reservations,<br/>status=confirmed, payment_status=paid, outbox emails; COMMIT
    API-->>B: order confirmed → /order-confirmation/{ref}
    R-->>API: webhook payment.captured / order.paid (signed)
    API->>DB: store event (unique event id) → same idempotent "mark paid" → no-op if already paid
```

## 2. Rules
1. **Amount authority.** The Razorpay order amount is `orders.grand_total × 100` (paise) computed by
   the backend. The browser never sends an amount.
2. **Signature check uses our stored `provider_order_id`**, not the `razorpay_order_id` echoed back by
   the browser.
3. **Signature is necessary but not sufficient.** We also fetch the payment and require
   `status == "captured"`, `amount == amount_paise`, `currency == "INR"` and
   `order_id == provider_order_id`. If the status is `authorized` (not yet captured), the order stays
   `pending_payment` with `payment_status=authorized`, and the webhook or the reconciliation job
   completes it later.
4. **One idempotent transition function**, `payments.service.mark_order_paid(order_id, attempt, source)`,
   is used by the verify endpoint, the webhook handler and the reconciliation job. It locks the order
   row (`FOR UPDATE`), returns early if the order is already paid, and otherwise commits stock,
   updates statuses, writes `order_events` and queues emails with idempotency keys.
5. **Webhooks**: the raw body is verified with `RAZORPAY_WEBHOOK_SECRET` *before* JSON parsing. Invalid
   signature → `400`, nothing stored. Valid → insert into `payment_events` (unique `event_id` from
   `x-razorpay-event-id`; a duplicate returns `200` immediately), then process. Handled events:
   `payment.authorized`, `payment.captured`, `payment.failed`, `order.paid`, `refund.processed`,
   `refund.failed`. Unknown events are stored and acknowledged.
6. **Failure / dismissal**: `payment.failed` or a closed pop-up leaves the order `pending_payment`
   (`payment_status=failed` with the error description). The customer can retry with
   `POST /payments/retry`, which creates a new Razorpay order for the same amount while the
   reservation is valid. Retries never create a second store order.
7. **Expiry**: after `payment_expires_at`, the background job marks the order `expired` and releases
   stock, after first checking Razorpay for any captured payment on its attempts (reconciliation).
8. **Late capture** (money arrives after expiry or cancellation): `mark_order_paid` tries to reserve
   and commit stock again. If that succeeds, the order is confirmed. If not, the order goes to
   `payment_review` and the admin dashboard shows it for a refund decision. We never silently keep
   money for an order we cannot fulfil.
9. **Duplicate checkout submissions**: `orders.idempotency_key` is unique. The same key returns the
   existing order. A different key with an identical still-pending cart returns the existing pending
   order instead of creating a second one.
10. **No fulfilment before payment**: admin status changes to `processing`/`shipped` are rejected
    unless `payment_status == paid`. Admins **cannot** set `payment_status` directly.
11. **Refunds** are requested by an admin with the `orders:refund` permission
    (`POST /v1/payments/{id}/refund` at Razorpay). The refund record moves `requested → pending →
    processed/failed` from API responses and `refund.*` webhooks.

## 3. Payment simulator (development/test only)
When `PAYMENT_PROVIDER=simulator`:
* `create_order` returns a fake `order_sim_…` id; no network calls are made.
* The checkout page shows a "Simulated payment — no money moves" dialog with **Pay** and **Fail**
  buttons. These call `/payments/simulator/pay`, which produces a Razorpay-style signature using
  `SIMULATOR_SECRET`. The browser then calls the normal `/payments/verify`, so the real verification
  code runs.
* Settings validation refuses to start the app with the simulator when `APP_ENV=production`.

## 3a. Implementation notes (Phase 6)
* Code: `services/payment_gateway.py` (Razorpay REST client + simulator), `services/payments.py`
  (`start_payment`, `verify_checkout`, `report_failure`, `retry_payment`, `mark_order_paid`,
  `sync_payment`, webhooks, `expire_and_reconcile`), `services/checkout.py`, `services/orders.py`.
* `POST /payments/report-failure` lets the pop-up's failure callback record the failure — the backend
  fetches the payment from the provider and records only what the provider says.
* A **different** captured payment for an order that is already paid creates a `refunds` row
  (`requested`, reason "Duplicate payment …") for an admin to execute.
* A newer checkout from the same cart replaces an unpaid pending order (it becomes `expired`,
  stock released, flagged `superseded`); a capture for a replaced or cancelled order always goes to
  `payment_review`.
* Webhook payloads are stored **sanitised** (ids, amounts, status, method, error code/description;
  no card, VPA, bank, email or phone fields).
* Simulator payment ids are signed with `SIMULATOR_SECRET`. Its list of payments per provider order
  lives in memory, so reconciliation (`run-jobs`, `reconcile-payments`) only finds simulated payments
  made in the same running process. Restarting the API also changes the default random secret.

## 4. Data stored
| Stored | Not stored |
|--------|-----------|
| Razorpay order id, payment id, refund id, amount, status, method (e.g. `upi`, `card`), error code/description, sanitised webhook payload | Card numbers, CVV, UPI PIN, bank credentials, key secret, webhook secret |
