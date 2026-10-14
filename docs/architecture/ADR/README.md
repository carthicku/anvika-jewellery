# Architecture Decision Records

An ADR captures one significant decision: the context, the choice, and its consequences.
When a decision changes, add a new ADR that supersedes the old one rather than rewriting history.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-modular-monolith.md) | Modular monolith (React SPA + FastAPI + PostgreSQL) | Accepted |
| [0002](0002-supabase-as-managed-postgres.md) | Supabase as managed PostgreSQL, not as the auth provider | Accepted |
| [0003](0003-cookie-auth-and-csrf.md) | Cookie-based JWT sessions with CSRF double-submit | Accepted |
| [0004](0004-sync-sqlalchemy.md) | Synchronous SQLAlchemy 2.x with psycopg 3 | Accepted |
| [0005](0005-razorpay-rest-integration.md) | Razorpay via REST + isolated development payment simulator | Accepted |
| [0006](0006-local-embedded-postgres.md) | Embedded PostgreSQL for local development | Accepted |
| [0007](0007-inventory-locking.md) | Row-locked inventory levels with a movement ledger | Accepted |
| [0008](0008-email-outbox.md) | Transactional email outbox | Accepted |
| [0009](0009-frontend-stack.md) | Frontend stack and API contract generation | Accepted |

To add a decision, copy [`0000-template.md`](0000-template.md) and increment the number.
