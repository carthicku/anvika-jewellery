# Anvika — Gold Jewellery Store

> "Anvika" is a working brand name taken from the project folder. It is configurable and will be
> replaced with the owner's confirmed brand.

A production-oriented e-commerce platform for a gold jewellery retailer in India:

* **Storefront**: refined, minimal and responsive. Collections, search, product pages with an
  itemised gold price breakdown, wishlist, cart, guest and account checkout.
* **Payments**: Razorpay, with server-side signature verification, signed webhooks and idempotent
  order processing. A clearly isolated payment simulator is available for local development.
* **After-sales**: order tracking, cancellation, returns/exchanges with restock and refunds, and
  verified-purchase reviews published only after staff approval.
* **Admin dashboard**: products, images, variants, inventory, orders, returns, reviews, gold rates,
  coupons, shipping, content, settings, staff roles and audit logs.
* **Operations**: data-integrity and RLS checks, a production web-server config (Caddy) and
  container files — see [DEPLOYMENT.md](docs/operations/DEPLOYMENT.md). **Not deployed yet.**

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, TypeScript 5.9 (strict), React Router 8, Tailwind CSS 4, Radix, TanStack Query, React Hook Form + Zod |
| Backend | Python 3.13, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, Argon2id, JWT cookies |
| Database | PostgreSQL 17 (Supabase in production; embedded PostgreSQL locally) |
| Tests | pytest, Vitest + Testing Library, Playwright |

## Project status
See **[PROJECT_STATUS.md](PROJECT_STATUS.md)** and the delivery report
**[docs/DELIVERY_REPORT.md](docs/DELIVERY_REPORT.md)**. Work proceeded in phases, tracked in
[tasks/MASTER_TASKS.md](tasks/MASTER_TASKS.md).

## Quick start
Full beginner-friendly instructions: **[docs/development/LOCAL_SETUP.md](docs/development/LOCAL_SETUP.md)**.

```bash
npm install && npm run db:start                     # terminal 1: local PostgreSQL 17 on port 54329

cd backend                                          # terminal 2: API
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
cp .env.example .env                                # then set SECRET_KEY in .env
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m app.cli seed
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8010

cd frontend                                         # terminal 3: website
npm install && cp .env.example .env && npm run dev  # http://localhost:5180
```

## Documentation
| Topic | Where |
|-------|-------|
| Working rules for Claude Code | [CLAUDE.md](CLAUDE.md) |
| Requirements, journeys, acceptance criteria | [docs/](docs/PRODUCT_REQUIREMENTS.md) |
| Architecture, schema, API, pricing, payments, security | [docs/architecture/](docs/architecture/SYSTEM_ARCHITECTURE.md) |
| Design system | [docs/design/](docs/design/DESIGN_SYSTEM.md) |
| Setup, env vars, migrations, testing | [docs/development/](docs/development/LOCAL_SETUP.md) |
| Deployment, backups, payments/email/shipping setup | [docs/operations/](docs/operations/DEPLOYMENT.md) |
| Test results, security and performance reviews, limitations | [docs/quality/](docs/quality/TEST_RESULTS.md) |
| Decisions and assumptions | [docs/ASSUMPTIONS_AND_DECISIONS.md](docs/ASSUMPTIONS_AND_DECISIONS.md) |

## Important
* Sample products, illustrations and gold rates are **fictional development data**.
* Tax rates and policy texts are **placeholders** that need professional review before launch.
* Never commit `.env` files or credentials.
