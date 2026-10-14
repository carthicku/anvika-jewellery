# Test Plan

How to run tests: [TESTING.md](../development/TESTING.md). Results: [TEST_RESULTS.md](TEST_RESULTS.md).

## 1. Test layers
| Layer | Tool | Scope | Runs against |
|-------|------|-------|--------------|
| Unit (backend) | pytest | Pricing engine, money rounding, allocation, state machine tables, signature functions, validators | Pure Python |
| API integration | pytest + FastAPI TestClient | Every endpoint's happy path + key failures, authorization, transactions, idempotency, concurrency | Real PostgreSQL (`anvika_test`) |
| Component | Vitest + Testing Library | Forms, filters, cart lines, price breakdown display, auth states, error/empty states | jsdom |
| End-to-end | Playwright | Journeys J1–J12 on desktop and mobile viewports + axe accessibility scans | Running app + seeded DB + payment simulator |
| Static | ruff, mypy, tsc, ESLint | Whole codebase | — |

## 2. Required backend tests (minimum)
| Area | Cases |
|------|-------|
| Auth | register (valid/duplicate/weak password), login (ok/wrong/unknown/rate-limited), refresh rotation and reuse detection, logout revokes, password reset (token single-use, expiry, no enumeration), change password revokes other sessions, inactive user blocked |
| Access control | customer → other customer's order/address/cart line = 404; customer → admin = 403; anonymous → admin = 401; guest order needs a token; **every** admin route has a permission dependency |
| CSRF | unsafe request without/with a mismatched token = 403; webhook exempt |
| Catalogue | public lists exclude drafts/archived; each filter; sorting order; pagination bounds; search with special characters; facets counts |
| Pricing | worked example from docs; each making-charge type; wastage; stones; fixed model; each discount type; best-discount selection; coupon percent with cap and min order; coupon allocation sums exactly; tax per component; rounding up/down/half; missing rate → not purchasable; Decimal-only (no float) |
| Cart | add/update/remove; quantity limits; stock limits; guest cookie; merge on login; price increase flagged; decrease auto-applied; accept-prices |
| Inventory | reserve/commit/release; constraints prevent negative stock; concurrent reservations of the last unit (threads) → exactly one succeeds; adjustment cannot go below reserved; ledger written for every change |
| Checkout | validation (PIN, phone, state, terms); out of stock; `PRICE_CHANGED` on stale expected_total; idempotency key returns the same order; pending order reused; no provider order before placing |
| Payments | valid signature + captured payment → paid; forged signature → 400, unpaid; amount mismatch → payment_review; authorized-not-captured → pending; retry after failure creates a new attempt, same order; late capture after expiry (stock available / not available) |
| Webhooks | invalid signature → 400 and nothing stored; valid → processed; duplicate event id → no double effect; unknown event stored |
| Orders | state machine allows/denies transitions; fulfilment blocked unless paid; cancellation effects (stock, refund record); order snapshot immutable after product edits |
| Admin | product CRUD + validation; image upload validation (type, size, real image); inventory adjust audited; gold rate preview, large-change confirmation, history, audit; coupons CRUD; settings update audited |
| Email | outbox row created once per idempotency key; file backend writes `.eml` and status `written_to_sink` |

## 3. Required frontend tests (minimum)
Header cart count; ProductCard rendering; FilterPanel updates URL; SortSelect; VariantPicker updates
the selection; PriceBreakdown renders backend rows; QuantityStepper limits; CouponForm error message;
PriceChangeNotice requires acceptance; AddressForm validation messages; Login/Register validation;
ProtectedRoute redirects; ErrorState retry calls refetch.

## 4. E2E journeys
J1–J12 from [USER_JOURNEYS.md](../USER_JOURNEYS.md), with a route smoke test that visits every
route.

## 5. Entry/exit criteria per phase
A phase is complete when: its tasks are done, all tests pass, new behaviour has tests, docs are
updated, and TEST_RESULTS.md has a dated entry with the real command output summary.
