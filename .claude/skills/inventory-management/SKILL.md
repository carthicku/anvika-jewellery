---
name: inventory-management
description: Use when changing stock levels, reservations, inventory adjustments, movement history, low-stock alerts, or any code path (checkout, payment, cancellation, returns, admin) that affects product availability. Protects against overselling with transactions, row locks and a movement ledger.
---

# Inventory management

Spec: `docs/architecture/INVENTORY_AND_ORDERS.md`, ADR-0007. Code:
`backend/app/services/inventory.py` — **the only module allowed to write `inventory_levels`,
`inventory_movements` and `inventory_reservations`.**

## Rules
1. `available = on_hand − reserved`. DB CHECK: `on_hand ≥ 0`, `reserved ≥ 0`, `reserved ≤ on_hand`.
2. Lock before change: `select(InventoryLevel).where(variant_id.in_(ids)).order_by(variant_id).with_for_update()`.
   Always lock in variant-id order (prevents deadlocks).
3. Every change inserts exactly one `inventory_movements` row per variant with the reason, deltas,
   order id and/or actor, and a note (required for admin adjustments).
4. Inventory functions never commit. The caller's transaction commits stock + order changes together.
5. Cart operations check availability but do not reserve. Reservation happens at order creation.
6. Admin adjustments cannot push `on_hand` below `reserved`.
7. Expiry/cancellation releases only `active` reservations for that order, exactly once (status
   moves to `released`).

## Operation table
| Function | on_hand | reserved | reason |
|----------|:-:|:-:|--------|
| `reserve(order, lines)` | – | +q | reservation |
| `release(order)` | – | −q | reservation_release |
| `commit(order)` | −q | −q | sale |
| `restock(order_items, reason)` | +q | – | cancellation_restock / return_restock |
| `adjust(variant, delta, note, actor)` | ±n | – | adjustment / initial |

## Required tests
- [ ] Reserve/commit/release math and ledger rows
- [ ] Concurrent reservations of the last unit from several threads → exactly one succeeds
- [ ] Release is idempotent (twice → once)
- [ ] Adjust below reserved → rejected
- [ ] Constraint violation surfaces as `OUT_OF_STOCK`/`CONFLICT`, not a 500
