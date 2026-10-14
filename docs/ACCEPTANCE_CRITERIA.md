# Acceptance Criteria

A criterion is **Passed** only with evidence (a test name or a manual check recorded in
[TEST_RESULTS.md](quality/TEST_RESULTS.md)). Otherwise it is **Unverified**. Current status lives in
[FEATURE_MATRIX.md](FEATURE_MATRIX.md) and [PROJECT_STATUS.md](../PROJECT_STATUS.md).

## Launch-readiness criteria (from the master brief §19)
| # | Criterion | Evidence required |
|---|-----------|-------------------|
| L1 | All required routes exist and behave appropriately | Route smoke test (`e2e/routes.spec.ts`) visits every route |
| L2 | Navigation and product discovery work | J1 e2e |
| L3 | Product information comes from the backend | No product fixtures in the production frontend bundle; e2e against the seeded DB |
| L4 | Cart totals are calculated by the backend | API tests; frontend has no price arithmetic (code review + grep) |
| L5 | Gold pricing is configurable and auditable | Pricing unit tests; admin gold-rate tests; order snapshot test |
| L6 | Authentication works securely | `test_auth.py` incl. rate limit, reset, session revoke |
| L7 | Customers cannot access others' data | `test_access_control.py` |
| L8 | Admin access is enforced server-side | `test_admin_permissions.py` (every admin route) |
| L9 | Product and inventory management work | Admin API tests + J8/J9 e2e |
| L10 | Checkout validates price, stock and shipping | `test_checkout.py` |
| L11 | Payment status only from verified provider events | `test_payments.py`, `test_webhooks.py` |
| L12 | Duplicate callbacks do not duplicate fulfilment | J5 |
| L13 | Order history is accurate | Account order tests |
| L14 | Important failures handled clearly | Error-state component tests; e2e failure paths |
| L15 | Migrations apply safely | `alembic upgrade head` on an empty DB + `alembic check` (no drift) in CI script |
| L16 | Production build succeeds | `npm run build` + backend import/startup check |
| L17 | Required automated tests executed | TEST_RESULTS.md with dates and counts |
| L18 | Known failures/skips documented | KNOWN_LIMITATIONS.md |
| L19 | No secrets in the repository | `scripts/check-secrets` scan + `.gitignore` review |
| L20 | Backup and recovery documented | BACKUP_AND_RESTORE.md |
| L21 | Deployment steps verified as far as possible | DEPLOYMENT.md + record of what was and was not verified |

## Feature-level criteria (selected, testable)
### Catalogue
* Filters (category, purity, metal colour, price range, availability, attributes) change the result
  set and the product count; combining filters uses AND across groups and OR within a group.
* Sorting `price_asc` returns non-decreasing `price_from`; `newest` orders by `published_at desc`.
* Filter state is in the URL; reloading the page reproduces the same results.
* Draft/archived products are never returned by public endpoints.
* Search handles `%`, `_`, quotes, emoji and 500-character input without errors.

### Product page
* Hallmark/HUID/certification sections render only if the product has that data.
* Variant change updates price, weight, SKU and stock status.
* Out-of-stock variants cannot be added to the cart (button disabled + API rejects).

### Cart
* Quantity limits 1–10 per line, and never more than the available stock.
* Price increase → line flagged and checkout disabled until accepted. A decrease is applied with a
  notice.
* An invalid/expired coupon shows a specific reason (expired, minimum not met, usage limit).

### Checkout
* Indian PIN code `^[1-9][0-9]{5}$`; phone `^[6-9][0-9]{9}$` (10-digit Indian mobile, `+91`
  optional); state chosen from the official list of states and UTs.
* The "Pay" button is disabled while submitting; double clicks create one order.
* The terms checkbox is required.
* The customer is never charged just by opening checkout (no provider order is created before
  "Place order & pay").

### Payments
* A forged signature → `400`, and the order stays unpaid.
* Correct signature but mismatched amount → order goes to `payment_review`, not paid.
* The same webhook delivered twice → processed once.

### Admin
* A customer token on any `/admin` API → `403`. An unauthenticated request → `401`.
* Gold rate change > 5% without confirmation → `422 CONFIRMATION_REQUIRED`.
* An admin cannot move an unpaid order to `processing`/`shipped`.
* Every create/update/delete in the admin writes an audit log entry.
