---
name: project-architecture
description: Use before adding a new module, endpoint, table, dependency, or cross-cutting change in this jewellery store, or when unsure where code belongs. Checks the change against the documented modular-monolith architecture (React SPA + FastAPI + PostgreSQL), layer rules and ADRs, and updates ADRs when a significant decision changes.
---

# Project architecture guardian

## Read first
1. `docs/architecture/SYSTEM_ARCHITECTURE.md` — layers and folder layout
2. `docs/ASSUMPTIONS_AND_DECISIONS.md` and `docs/architecture/ADR/README.md` — decisions already made
3. The domain doc for the area being changed (PRICING_ENGINE, PAYMENT_FLOW, INVENTORY_AND_ORDERS,
   AUTHENTICATION, SECURITY_MODEL, DATABASE_SCHEMA, API_CONTRACT)

## Placement rules
| Kind of code | Goes in |
|--------------|---------|
| HTTP parsing, status codes, cookies | `backend/app/api/v1/routes/<domain>.py` (admin: `routes/admin/`) |
| Business rules, transactions, ownership checks | `backend/app/services/<domain>.py` |
| Tables | `backend/app/models/<domain>.py` + an Alembic migration |
| Request/response shapes | `backend/app/schemas/<domain>.py` (`…In` / `…Out`) |
| Cross-cutting (config, errors, security, logging, money) | `backend/app/core/` |
| Server data in the UI | `frontend/src/api/queries/<domain>.ts` hooks |
| Visual building blocks | `frontend/src/components/ui|layout|product|…` |
| Route screens | `frontend/src/pages/<area>/` |

## Checklist for any change
- [ ] Routers call services; services never import FastAPI request/response objects.
- [ ] No business logic (prices, stock, status changes, permissions) in the frontend or in routers.
- [ ] No new service/process/queue. This is a modular monolith (ADR-0001). Justify in an ADR if you
      think otherwise.
- [ ] No new dependency unless the standard library or an existing dependency cannot do the job.
      Note the reason in the commit message.
- [ ] No abstraction with a single implementation "for the future", except the documented
      interfaces (payment gateway, email sender, storage, shipping provider).
- [ ] Schema changes come with a migration and an update to `DATABASE_SCHEMA.md`/`ER_DIAGRAM.md`.
- [ ] API changes update `backend/openapi.json` (export) and the frontend generated types, and
      `API_CONTRACT.md` if a route was added or removed.

## When a significant decision changes
Copy `docs/architecture/ADR/0000-template.md` to the next number, mark the old ADR
"Superseded by ADR-XXXX", update the ADR index and `ASSUMPTIONS_AND_DECISIONS.md` §4.
