# ADR-0008: Transactional email outbox

- Status: Accepted
- Date: 2026-10-14

## Context
Emails must not be sent twice (e.g. duplicate webhooks) and must not be lost if the SMTP server is
briefly unavailable. Sending must not happen inside a database transaction that may roll back.

## Decision
Business code inserts a row into `email_outbox` with a unique `idempotency_key`
(e.g. `order_confirmation:<order_id>`) in the same transaction as the business change. A dispatcher
sends pending rows after commit using the configured backend:
`file` (writes `.eml` files to `backend/var/mail/` — the development sink), `console`, or `smtp`.
Status values distinguish `sent` (accepted by an SMTP server) from `written_to_sink`.

## Consequences
- We never claim an email was delivered when only a sink was used.
- Retries are bounded (max attempts) and failures are visible to administrators.
