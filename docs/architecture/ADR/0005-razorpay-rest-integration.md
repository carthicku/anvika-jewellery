# ADR-0005: Razorpay via REST and an isolated development payment simulator

- Status: Accepted
- Date: 2026-10-14

## Context
Razorpay is the payment provider. The official Python SDK pulls in extra dependencies; the REST API
surface we need is small (create order, fetch payment, create refund). Razorpay test keys are not
yet available, but automated tests and local end-to-end testing still need a payment step.

## Decision
- `backend/app/services/payment_gateway.py` (`RazorpayGateway`) calls `https://api.razorpay.com/v1` with `httpx` using
  HTTP Basic auth (key id + key secret, backend only).
- Checkout signature: `HMAC_SHA256(razorpay_order_id + "|" + razorpay_payment_id, key_secret)`.
- Webhook signature: `HMAC_SHA256(raw_request_body, webhook_secret)` from `X-Razorpay-Signature`;
  `X-Razorpay-Event-Id` is stored with a unique constraint for idempotency.
- After a valid checkout signature, the backend **also fetches the payment** from Razorpay and checks
  `status`, `amount`, `currency` and `order_id` before marking an order paid.
- `PAYMENT_PROVIDER=simulator` enables `backend/app/services/payment_gateway.py` (`SimulatorGateway`), which mimics
  Razorpay's signatures using a local secret. It is rejected at startup when `APP_ENV=production`,
  the UI shows a "SIMULATED PAYMENT — no money moves" notice, and such orders keep
  `provider='simulator'` permanently.

## Consequences
- The same verification code path is exercised by tests and by real Razorpay.
- Razorpay API changes must be tracked manually (see `docs/operations/PAYMENT_PROVIDER_SETUP.md`).
