# ADR-0009: Frontend stack and API contract generation

- Status: Accepted
- Date: 2026-10-14

## Decision
- React 19 + Vite 8 + TypeScript 6.0 (strict). TypeScript 7 is avoided until typescript-eslint
  supports it.
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
