# ADR-0009: Frontend stack and API contract generation

- Status: Accepted
- Date: 2026-10-14

## Decision
- React 19 + Vite 8 + TypeScript 5.9 (strict). openapi-typescript 7 requires TypeScript 5 and
  typescript-eslint supports < 6.1, so TS 6/7 are avoided until the tooling catches up. ESLint 10 with
  `eslint-plugin-jsx-a11y-x` (maintained fork; the original plugin does not support ESLint 10).
- React Router 8 in data mode (`createBrowserRouter` from `react-router`, `RouterProvider` from
  `react-router/dom`; `react-router-dom` no longer exists in v8).
- Tailwind CSS v4; design tokens in `frontend/src/styles/index.css` under `@theme`.
- Accessible primitives from the unified `radix-ui` package, wrapped in our own components in
  `frontend/src/components/ui/` (shadcn/ui style, hand-written so the project owns the code).
- TanStack Query for all server state (including the cart, which lives on the server). A small React
  context for UI-only state (mobile menu, toasts). No global state library.
- React Hook Form + Zod 4 for forms.
- The backend writes `backend/openapi.json` (`python -m app.cli export-openapi`); the frontend runs
  `npm run gen:api` (openapi-typescript) to produce `frontend/src/api/schema.d.ts`, and
  `openapi-fetch` provides typed calls.
- Page metadata uses React 19's native `<title>`/`<meta>` hoisting (no Helmet dependency).

## Consequences
- Contract drift between frontend and backend becomes a TypeScript compile error once types are
  regenerated.
