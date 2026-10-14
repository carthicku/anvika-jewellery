# Phase 4 — Authentication and Customer Accounts

Goal: secure customer accounts with enforced permissions.

## Tasks
- [ ] Models + migration: users, user_sessions, user_tokens, addresses, wishlist_items
- [ ] Argon2id hashing with rehash-on-login; password policy
- [ ] JWT access + rotating refresh with reuse detection; cookie helpers; `get_current_user`, `require_permission`
- [ ] Permission map (`app/core/permissions.py`) + test that every admin route declares a permission
- [ ] Postgres-backed rate limiter for login/register/forgot/reset/resend/contact/newsletter/pincode
- [ ] Endpoints: csrf, register, login, refresh, logout, logout-all, me, verify-email, resend-verification,
      forgot-password, reset-password, change-password, sessions list/revoke
- [ ] Email outbox (model + idempotent enqueue + file/console/memory/smtp senders) + verify/reset templates
- [ ] `/me/profile`, `/me/addresses` CRUD (ownership enforced; Indian PIN/phone/state validation)
- [ ] Wishlist API + merge; guest wishlist in localStorage
- [ ] CLI: `create-admin` (prompted password), `create-customer` (dev only), `deactivate-user`
- [ ] Frontend: login, register, forgot/reset password, verify email, account layout, profile, addresses,
      wishlist, security (change password, sessions, logout everywhere), route guards
- [ ] Tests: per TEST_PLAN auth + access-control sections; frontend form tests

## Acceptance
J2 passes; access-control tests pass; no token readable by JS.
