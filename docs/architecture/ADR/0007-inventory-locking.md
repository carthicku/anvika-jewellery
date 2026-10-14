# ADR-0007: Row-locked inventory levels with a movement ledger

- Status: Accepted
- Date: 2026-10-14

## Context
Much fine jewellery is one-of-a-kind (stock of 1). Two customers must never both pay for it.

## Decision
- `inventory_levels(variant_id PK, on_hand, reserved, low_stock_threshold)` with
  `CHECK (on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand)`.
- Every change locks the row with `SELECT ... FOR UPDATE` (rows locked in a stable order — sorted by
  variant id — to avoid deadlocks) inside the same transaction as the order change.
- Order creation reserves stock (`reserved += qty`) and records an `inventory_reservations` row with
  an expiry. Verified payment commits it (`on_hand -= qty; reserved -= qty`). Expiry or cancellation
  releases it.
- Every change writes an `inventory_movements` row (append-only ledger) with reason, actor and order.

## Consequences
- Overselling is prevented by the database even if application logic has a bug.
- A payment that arrives after its reservation expired is re-reserved if stock allows; otherwise the
  order moves to `payment_review` for a human decision (usually a refund).
