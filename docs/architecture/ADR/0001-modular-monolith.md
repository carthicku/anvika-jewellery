# ADR-0001: Modular monolith

- Status: Accepted
- Date: 2026-10-14

## Context
A single jewellery retailer needs a storefront, checkout, payments and an admin dashboard. The team
is small and learning. Microservices would add network failure modes, deployment complexity and
distributed transactions — especially dangerous for inventory and payments.

## Decision
Build **one** FastAPI backend organised into domain modules (auth, catalogue, pricing, cart,
checkout, orders, payments, inventory, shipping, content, admin) and **one** React SPA that contains
both the storefront and the `/admin` area (the admin area is lazy-loaded as a separate chunk).
PostgreSQL is the single source of truth.

## Consequences
- Checkout, inventory and payment updates can share one database transaction.
- Module boundaries are enforced by convention (routers → services → models), documented in
  `docs/development/CODE_CONVENTIONS.md`, not by network calls.
- Scaling is vertical, or horizontal replicas of the same app, which is ample for this business.
