---
name: react-frontend
description: Use when writing or reviewing code in frontend/ (React 19, Vite, TypeScript, React Router 8, TanStack Query, React Hook Form + Zod, Tailwind v4, Radix). Covers conventions, typed API usage, data states, forms, routing and frontend tests.
---

# React frontend conventions

## Stack facts (verified 2026-10-14)
* React Router **8**: import from `react-router`; `RouterProvider` comes from `react-router/dom`.
  `react-router-dom` no longer exists. Data mode (`createBrowserRouter`), with route `lazy` for
  admin/account chunks.
* TypeScript pinned to **5.9.x** (openapi-typescript 7 requires TS 5; typescript-eslint supports < 6.1).
* ESLint 10 with `eslint-plugin-jsx-a11y-x` (the original jsx-a11y plugin does not support ESLint 10).
* Dev ports: web **5180**, API **8010** (5173/8000 are used by other software on the dev machine).
* Tailwind v4 (`@tailwindcss/vite`, tokens in `src/styles/index.css` `@theme`).
* Zod 4 + `@hookform/resolvers` 5.

## Rules
1. **Typed API only.** Call the backend through `src/api/client.ts` (openapi-fetch typed by the
   generated `src/api/schema.d.ts`). After backend changes:
   `cd backend && .venv/Scripts/python -m app.cli export-openapi && cd ../frontend && npm run gen:api`.
2. **Server state = TanStack Query.** Hooks live in `src/api/queries/<domain>.ts`; keys come from
   `src/api/queryKeys.ts`. Mutations invalidate affected keys. The cart is server state.
3. **No business logic.** Never compute prices, taxes, discounts, totals or stock. Money arrives as
   strings; display it with `<Price value="…"/>` (Intl `en-IN`, INR). Never `parseFloat` money for
   arithmetic.
4. **Every data view handles four states**: `Skeleton` while loading, `ErrorState` with `refetch`,
   `EmptyState`, success.
5. **Forms**: React Hook Form + Zod schema from `src/lib/validation/`; show server
   `VALIDATION_ERROR` `details.fields` on the matching inputs (`setError`); disable submit while
   pending; move focus to the first error.
6. **Errors**: API errors are `ApiError` with `code`, `message`, `requestId`. Branch on `code`
   (`PRICE_CHANGED`, `OUT_OF_STOCK`, `RATE_LIMITED`, …), not on message text.
7. **Auth UI is cosmetic.** Route guards improve UX; the backend enforces access.
8. **Accessibility**: semantic HTML, Radix for complex widgets, labels on every input, `aria-label` on
   icon buttons, polite live region for cart updates.
9. **Storage**: `localStorage` only for non-sensitive conveniences (guest wishlist slugs, recently
   viewed), always wrapped in try/catch. Never store tokens.
10. **Secrets**: none. `VITE_*` values are public.

## Tests
* Vitest + Testing Library: query by role/label; test behaviour (clicking, typing, URL changes),
  not implementation details. Mock the network with the shared `server` helper in
  `src/test/`, not by mocking hooks.
* Playwright specs in `frontend/e2e/`; prefer `getByRole`.

## Before finishing
`npm run typecheck && npm run lint && npm test` must pass. Then run the app and look at the change at
mobile and desktop widths.
