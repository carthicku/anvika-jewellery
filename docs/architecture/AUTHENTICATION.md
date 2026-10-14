# Authentication and Authorization

Decision record: [ADR-0003](ADR/0003-cookie-auth-and-csrf.md).

## 1. Passwords
* Hashed with **Argon2id** (`argon2-cffi`, library defaults: time cost 3, memory 64 MiB, parallelism 4).
  Hashes are upgraded transparently on login when parameters change (`check_needs_rehash`).
* Requirements: 10–128 characters, not entirely digits, not equal to the email address. The rules
  are checked on both the frontend (Zod) and the backend (Pydantic + service).
* Passwords are never logged, returned, or stored in plain text.

## 2. Sessions and cookies

| Cookie | Contents | Lifetime | Flags |
|--------|----------|----------|-------|
| `access_token` | JWT HS256 `{sub, sid, role, iat, exp, typ:"access"}` | 15 min | HttpOnly, Secure*, SameSite=Lax, Path=/ |
| `refresh_token` | 256-bit random, stored as SHA-256 in `user_sessions` | 30 days (sliding, absolute max 90 days) | HttpOnly, Secure*, SameSite=Strict, Path=/api/v1/auth |
| `csrf_token` | random 32 bytes (URL-safe) | session | **not** HttpOnly (JS must read it), Secure*, SameSite=Strict, Path=/ |
| `cart_token` | random 32 bytes; SHA-256 stored in `carts.token_hash` | 60 days | HttpOnly, Secure*, SameSite=Lax, Path=/api |

\* `Secure` is on whenever `COOKIE_SECURE=true` (forced on in production; off on `http://localhost`).

### Request authentication (`get_current_user`)
1. Read and verify the `access_token` JWT (signature, `exp`, `typ`).
2. Load `user_sessions` row by `sid` joined with `users`; reject if the session is revoked/expired or
   the user is inactive. → instant logout/deactivation.
3. The role is taken from the **database row**, not the JWT claim.

### Refresh flow
`POST /auth/refresh` reads `refresh_token`, finds the session by hash, checks expiry, issues a new
refresh token (stores the new hash, keeps the old one as `previous_refresh_token_hash`), and issues a
new access token. If a request presents a token equal to `previous_refresh_token_hash`, the token was
replayed — the whole session is revoked. Exception: within 20 seconds of a rotation the old token gets
`409 REFRESH_RACE` instead (two browser tabs refreshing at the same moment); the browser simply
retries with the cookies the other tab already received. The frontend calls refresh automatically once when it
receives `401 SESSION_EXPIRED`, then retries the original request whatever the outcome: if the refresh
failed the backend has cleared the dead cookies, so public pages keep working as a guest and protected
ones redirect to sign-in.

### CSRF
Double-submit: unsafe methods must send header `X-CSRF-Token` equal to the `csrf_token` cookie.
The middleware also rejects unsafe requests whose `Origin` header is present and not in
`ALLOWED_ORIGINS`. Webhooks are exempt (HMAC authenticated). `SameSite` cookies give a second layer.

## 3. Account flows
| Flow | Behaviour |
|------|-----------|
| Register | Creates `role=customer`. Starts a session. A verification email is queued and the account area shows a banner until it is confirmed. Registering with an existing email returns `409 EMAIL_IN_USE` (a deliberate usability trade-off: it reveals that the address has an account; limited to 10 registrations per IP per hour). |
| Login | Generic `INVALID_CREDENTIALS` for unknown email, wrong password or deactivated account; a dummy hash is verified for unknown emails so timing is similar. Rate limits: 30 attempts / 15 min per IP and 10 / 15 min per account. |
| Forgot password | Always `202 Accepted` with the same message. If the account exists, a single-use token valid for 30 min is emailed; requesting again invalidates older links. Limits: 10 / hour per IP, 3 / hour per email. Outbox rows drop the link once the email is sent. |
| Reset password | Token must be unused and unexpired; sets password, marks token used, revokes **all** sessions. |
| Change password | Requires current password; revokes all other sessions. |
| Verify email | Single-use token valid 48 h. |
| Logout | Revokes the current session row and clears cookies. The browser navigates away first, then forgets the user (so the account-page guard never bounces the customer to sign-in). |
| Sign in redirect | `?next=` is honoured only for same-site paths (`/…`, never `//host` or absolute URLs) — see `frontend/src/lib/forms.ts`. |
| Guest → account | On login/registration, the guest cart is merged into the user's cart; the browser wishlist is merged via `/wishlist/merge`. |

## 4. Roles and permissions

Roles live in `users.role`. Permissions are a **fixed map in code** (`app/core/permissions.py`):

| Permission | customer | staff | admin |
|------------|:-:|:-:|:-:|
| Shop, manage own profile/addresses/orders/wishlist | ✅ | ✅ | ✅ |
| `dashboard:view` | | ✅ | ✅ |
| `catalogue:write` (products, categories, collections, images) | | ✅ | ✅ |
| `inventory:write` | | ✅ | ✅ |
| `orders:write` (status, shipments, notes, returns) | | ✅ | ✅ |
| `orders:refund` (trigger provider refunds) | | | ✅ |
| `customers:view` | | ✅ | ✅ |
| `content:write` (pages, reviews moderation) | | ✅ | ✅ |
| `promotions:write` (discounts, coupons) | | | ✅ |
| `pricing:write` (gold rates, tax settings) | | | ✅ |
| `settings:write` (store, shipping) | | | ✅ |
| `audit:view` | | | ✅ |
| `users:manage` (staff roles, deactivate) | | | ✅ |

Every admin route declares its permission with `Depends(require_permission("..."))`. A test asserts
that **every** route under `/api/v1/admin` has such a dependency.

Ownership: customer-facing services always filter by `user_id = current_user.id` (or a valid guest
order access token). Someone else's resource returns `404`, not `403`, so its existence is not
revealed.

## 5. Provisioning the first administrator
No default admin account exists and no admin password lives in source code. Run on a trusted machine
with access to the database:

```bash
cd backend
.venv/Scripts/python -m app.cli create-admin --email owner@example.com --name "Store Owner"
# You are prompted twice for a password (not echoed, not logged).
```
The command refuses weak passwords and records an audit-log entry. To promote an existing staff
user, an admin uses **Admin → Users** (audited).

## 6. Admin MFA (planned, Phase 7)
Optional TOTP (RFC 6238) for staff/admin accounts, with the secret encrypted at rest using
`MFA_ENCRYPTION_KEY`. Until it is implemented, it is listed in
[KNOWN_LIMITATIONS](../quality/KNOWN_LIMITATIONS.md).
