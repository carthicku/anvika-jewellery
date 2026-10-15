# Test Results

Append a dated entry after each verified checkpoint. Record the real command, counts and failures.
Never record a result that was not actually observed.

## Format
```
### YYYY-MM-DD — <checkpoint name>
| Suite | Command | Result |
|-------|---------|--------|
| Backend | `pytest` | 123 passed, 0 failed, 2 skipped (reason) |
Notes / failures / follow-ups.
```

---

### 2026-10-14 — Phase 0 (planning)
No application code exists yet, so no tests have been run. Environment checks performed:
| Check | Result |
|-------|--------|
| Node.js | v24.20.0 |
| npm | 11.19.0 |
| Python | 3.13.15 via `py -3.13` (Python 3.12 registration is broken on this machine) |
| Git | 2.56.0 |
| Docker / psql | not installed |
| Embedded PostgreSQL probe | `embedded-postgres@17.10.0-beta.17` started PostgreSQL 17.10 on Windows and answered `select version()` |

### 2026-10-14 — Phase 0 checkpoint
| Suite | Command | Result |
|-------|---------|--------|
| Docs & skills consistency | `py -3.13 scripts/check_docs.py` | OK: 54 required files present, 91 relative links resolve, 11 skills valid |
| Checker self-test | planted a broken link and a malformed skill | Both reported, exit code 1 |

### 2026-10-14 — Phase 1 checkpoint (Foundation)
| Suite | Command | Result |
|-------|---------|--------|
| All static checks + unit/API tests + build | `powershell -File scripts/check.ps1` | All checks passed |
| Backend tests | `pytest -q` | 35 passed |
| Backend lint/types | `ruff check`, `ruff format --check`, `mypy app` (strict) | clean |
| Migrations | `alembic upgrade head` on empty test DB (via fixtures) + `alembic check` | no drift |
| Frontend unit tests | `vitest run` | 9 passed (2 files) |
| Frontend typecheck / lint / format | `tsc -b`, `eslint --max-warnings 0`, `prettier --check` | clean |
| Frontend build | `vite build` | OK — JS 357 kB (112 kB gzip), CSS 18 kB (4.2 kB gzip) |
| E2E smoke | `playwright test` (desktop-chrome + mobile-chrome) | 4 passed |
| Manual | `curl /api/v1/health?deep=true` on :8010 | 200, database ok, migration 6bce87049df5, CSP + X-Request-ID headers present |

Notes: first E2E run failed because another local project was serving port 5173 and Playwright reused it;
frontend moved to port 5180 (and API to 8010, since 8000 was also taken).

### 2026-10-14 — Phases 2 & 3 checkpoint (catalogue + storefront)
| Suite | Command | Result |
|-------|---------|--------|
| Full static + unit/API + build | `powershell -File scripts/check.ps1` | All checks passed |
| Backend | `pytest -q` | 134 passed (37 pricing unit tests; catalogue, content and database-safety API tests) |
| Frontend unit | `vitest run` | 21 passed (3 files) |
| End-to-end | `playwright test` (desktop-chrome + mobile-chrome) | 25 passed, 1 skipped (keyboard test is desktop-only) |
| Accessibility | axe (WCAG 2.0/2.1/2.2 A+AA tags) on 7 pages × 2 viewports | 0 serious/critical violations |
| Seed | `python -m app.cli seed` ×2 | identical row counts (idempotent) |
| Manual | Screenshots at 1440 px and 390 px of home, listing, product and guide pages | reviewed; price-format consistency and "From" price fixes applied |

Defects found and fixed during this checkpoint: local PostgreSQL cluster was WIN1252 (UTF-8 now
enforced); timestamps returned in local time (sessions forced to UTC); SQLAlchemy 2.1 DISTINCT ON
deprecation; React Router setSearchParams overwrite when setting two keys; focus moved to <main> on
first load; focus lost after closing header dialogs; JSON-LD `<` escaping.

### 2026-10-14 — Phase 4 checkpoint (authentication & accounts)
| Suite | Command | Result |
|-------|---------|--------|
| Full static + unit/API + build | `powershell -File scripts/check.ps1` | All checks passed (initial JS 93 kB gzip) |
| Backend | `pytest -q` | 168 passed (auth 21, account 7, permissions/CLI 5, plus earlier suites) |
| Frontend unit | `vitest run` | 33 passed (4 files), stable across repeated runs |
| End-to-end | `playwright test` ×3 (desktop + mobile, backend with `RATE_LIMIT_ENABLED=false`) | 30 passed each run (keyboard test desktop-only, sideways-scroll test mobile-only) |

New E2E coverage: J2 account journey (register → addresses add/edit/delete → sign out → sign in),
wrong-password message, and "no page scrolls sideways on a phone" for 10 routes.

### 2026-10-14 — Phase 5 checkpoint (cart & pricing)
| Suite | Command | Result |
|-------|---------|--------|
| Full static + unit/API + build | `powershell -File scripts/check.ps1` | All checks passed (initial JS 94 kB gzip) |
| Backend | `pytest -q` | 190 passed (17 cart API tests added; 6 rupee-format tests) |
| Frontend unit | `vitest run` | 39 passed (5 files) |
| End-to-end | `playwright test` ×2 (desktop + mobile, rate limits off) | 34 passed each run |

New E2E coverage: cart journey (one-of-a-kind quantity limit, add two pieces, change quantity,
WELCOME5 coupon with cap, remove line, no sideways scrolling with items) and expired-coupon message.

### 2026-10-15 — Phase 6 checkpoint (checkout, payments, orders)
| Suite | Command | Result |
|-------|---------|--------|
| Full static + unit/API + build | `powershell -File scripts/check.ps1` | All checks passed (initial JS 94 kB gzip; checkout chunk 5.4 kB gzip) |
| Backend | `pytest -q` | 243 passed (21 checkout, 31 payment/webhook/expiry/cancel, 1 two-connection concurrency) |
| Frontend unit | `vitest run` | 44 passed (6 files; 5 new checkout tests) |
| End-to-end | `playwright test` ×2 (desktop + mobile, rate limits off, simulator) | 42 passed each run |

New E2E coverage: guest checkout → simulated payment → confirmation → cancellation (J3, J11);
failed payment → retry → paid (J4); signed-in checkout → order history → cancel; axe scan of the
checkout page with delivery options. After both runs the dev stock levels were unchanged (test
orders are cancelled, which restocks them). Razorpay itself was tested against a mocked API only.

### 2026-10-15 — Phase 7 checkpoint (admin, before returns/reviews)
| Suite | Command | Result |
|-------|---------|--------|
| Full static + unit/API + build | `powershell -File scripts/check.ps1` | All checks passed (storefront initial JS 94.5 kB gzip; admin in separate chunks) |
| Backend | `pytest -q` | 291 passed (+48 admin API tests) |
| Frontend unit | `vitest run` | 44 passed |
| End-to-end | `playwright test` ×2 (desktop + mobile) | 52 passed each run |

New E2E coverage (`e2e/admin.spec.ts`): admin sign-in and navigation without sideways scrolling;
create product → photo upload → publish → visible in store → stock adjustment → archive (J8, J9);
prepare → cancel → send refund (simulator); customers see "This area is for store staff" (J10);
axe on dashboard, product editor, orders and gold rates (desktop + phone). The E2E admin is created
by the dev-only `python -m app.cli e2e-admin` with a fresh random password per run.
