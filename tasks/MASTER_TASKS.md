# Master Task Tracker

Mark a task `[x]` only after it is verified (tests pass / manually checked and recorded).
Phase details are in the linked files. Milestones and acceptance criteria are in
[IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md).

| Phase | File | Status |
|-------|------|--------|
| 0 Discovery & planning | (this file, §Phase 0) | ✅ complete |
| 1 Foundation | [PHASE_01_FOUNDATION.md](PHASE_01_FOUNDATION.md) | ✅ complete |
| 2 Design system & storefront | [PHASE_02_DESIGN_SYSTEM.md](PHASE_02_DESIGN_SYSTEM.md) | ⬜ |
| 3 Database-backed catalogue | [PHASE_03_CATALOGUE.md](PHASE_03_CATALOGUE.md) | 🟡 next |
| 4 Auth & accounts | [PHASE_04_AUTH_AND_ACCOUNTS.md](PHASE_04_AUTH_AND_ACCOUNTS.md) | ⬜ |
| 5 Cart & pricing | [PHASE_05_CART_AND_CHECKOUT.md](PHASE_05_CART_AND_CHECKOUT.md) | ⬜ |
| 6 Checkout, payments & orders | [PHASE_06_PAYMENTS_AND_ORDERS.md](PHASE_06_PAYMENTS_AND_ORDERS.md) | ⬜ |
| 7 Administration | [PHASE_07_ADMIN_AND_INVENTORY.md](PHASE_07_ADMIN_AND_INVENTORY.md) | ⬜ |
| 8 Quality & launch prep | [PHASE_08_POLISH_AND_LAUNCH.md](PHASE_08_POLISH_AND_LAUNCH.md) | ⬜ |

> Phase numbering note: the brief lists "Cart and pricing" (5) and "Checkout, payments and orders"
> (6). Files `PHASE_05_CART_AND_CHECKOUT.md` covers cart + pricing + coupons, and
> `PHASE_06_PAYMENTS_AND_ORDERS.md` covers checkout, payments and orders.

## Phase 0 — Discovery & planning
- [x] Inspect the environment (Node 24.20, npm 11.19, Python 3.13.15, Git 2.56; no Docker/psql)
- [x] Verify a local PostgreSQL option (embedded-postgres 17.10 works)
- [x] Check current package versions & peer compatibility (TypeScript pinned to 5.9.x — see ADR-0009)
- [x] Verify React Router 8 and Razorpay API facts against official sources
- [x] Assumptions and decisions + ADRs 0001–0009
- [x] Architecture docs (system, schema, ER, API, auth, pricing, payments, inventory, security)
- [x] Product docs (requirements, journeys, feature matrix, acceptance criteria)
- [x] Design docs (tokens with measured contrast, components, responsive, accessibility)
- [x] Developer, operations and quality docs
- [x] Claude Code skills (11) under `.claude/skills/`
- [x] CLAUDE.md, README, PROJECT_STATUS, IMPLEMENTATION_PLAN, CHANGELOG, .env.example
- [x] Structure verification (all files present, skill frontmatter valid, links resolve)
