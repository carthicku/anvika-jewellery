# ADR-0003: Cookie-based JWT sessions with CSRF double-submit

- Status: Accepted
- Date: 2026-10-14

## Context
Tokens stored in `localStorage` can be stolen by any XSS bug. The spec prefers HTTP-only cookies.

## Decision
- `access_token` cookie: JWT (HS256), 15-minute lifetime, `HttpOnly; Secure; SameSite=Lax; Path=/`.
  Its `sid` claim points to a row in `user_sessions`; each request verifies that the session is not
  revoked and the user is active, so logout and password changes take effect immediately.
- `refresh_token` cookie: 256-bit random opaque value (stored only as a SHA-256 hash), 30-day
  lifetime, `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth`. Rotated on every refresh; reuse
  of the previous token revokes the session (theft detection).
- `csrf_token` cookie (readable by JavaScript) + `X-CSRF-Token` header must match on every unsafe
  request (POST/PUT/PATCH/DELETE) — the double-submit pattern. The Razorpay webhook is exempt (it is
  authenticated by HMAC signature instead).
- The frontend and API are served from the same site (Vite proxy in development; reverse proxy or
  `api.` subdomain in production).

## Consequences
- No auth tokens are ever readable by JavaScript.
- A cross-site deployment (different registrable domains) would require `SameSite=None` and is not
  supported without revisiting this ADR.
