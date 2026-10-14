# Phase 4 — Authentication and Customer Accounts  ✅ complete (2026-10-14)

Goal: secure customer accounts with enforced permissions.

## Tasks
- [x] Models + migration: users, user_sessions, user_tokens, addresses, wishlist_items
- [x] Argon2id hashing with rehash-on-login; password policy
- [x] JWT access + rotating refresh with reuse detection; cookie helpers; `get_current_user`, `require_permission`
- [x] Permission map (`app/core/permissions.py`) + test that every admin route declares a permission
- [x] Postgres-backed rate limiter for login/register/forgot/reset/resend/contact/newsletter/pincode
- [x] Endpoints: csrf, register, login, refresh, logout, logout-all, me, verify-email, resend-verification,
      forgot-password, reset-password, change-password, sessions list/revoke
- [x] Email outbox (model + idempotent enqueue + file/console/memory/smtp senders) + verify/reset templates
- [x] `/me/profile`, `/me/addresses` CRUD (ownership enforced; Indian PIN/phone/state validation)
- [x] Wishlist API + merge; guest wishlist in localStorage
- [x] CLI: `create-admin` (prompted password), `create-customer` (dev only), `deactivate-user`
- [x] Frontend: login, register, forgot/reset password, verify email, account layout, profile, addresses,
      wishlist, security (change password, sessions, logout everywhere), route guards
- [x] Tests: per TEST_PLAN auth + access-control sections; frontend form tests

## Acceptance
J2 passes; access-control tests pass; no token readable by JS.

Notes:
- Address update is `PUT` (full replace) rather than `PATCH`; wishlist endpoints are keyed by slug.
- Admin TOTP MFA remains a Phase 7 item (KNOWN_LIMITATIONS).
- Defects found by the new tests and fixed: account page overflowed sideways on phones (grid item
  min-width), sign-out could bounce to the sign-in page (guard raced the redirect), server-error
  mapping inside render, E2E locators ambiguous with the footer newsletter field.
