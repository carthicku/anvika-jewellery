# ADR-0004: Synchronous SQLAlchemy 2.x with psycopg 3

- Status: Accepted
- Date: 2026-10-14

## Context
Async SQLAlchemy adds complexity (`await` everywhere, lazy-loading pitfalls) that is hard for
beginners. Store traffic is modest.

## Decision
Use the synchronous SQLAlchemy 2.x API (typed `Mapped[...]` models, `select()` queries) with the
`psycopg` 3 driver. Route handlers that touch the database are plain `def` functions; FastAPI runs
them in its thread pool. External HTTP calls (Razorpay) use a synchronous `httpx.Client` with
timeouts.

## Consequences
- Simple, explicit code. One request = one session = one transaction (committed by the service
  layer at the end of a successful unit of work).
- Concurrency is bounded by the thread pool size and DB pool size — sufficient here.
