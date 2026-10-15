# Phase 8 — Quality and Launch Preparation

Goal: an evidence-based deployment-ready candidate with remaining external dependencies listed.

## Tasks
- [x] Complete the E2E suite J1–J12 (desktop + mobile projects) + route smoke test + axe scans
- [ ] Manual keyboard pass and responsive pass (recorded) — automated keyboard flow and 375/768/1280
      layout checks done (`journeys.spec.ts`); a pass by a person remains (production checklist)
- [x] Security review against SECURITY_MODEL (record evidence per control); `pip-audit`, `npm audit`
- [x] SEO: titles/descriptions, canonical, OG, Product JSON-LD (verified fields only), robots.txt,
      sitemap, `noindex` for private routes
- [x] Performance: bundle analysis, image sizes, Lighthouse runs recorded; API query EXPLAIN checks
- [x] Deployment files: backend Dockerfile, `deploy/docker-compose.prod.yml`, `deploy/Caddyfile`
      (headers, CSP, caching) — Caddyfile verified locally; Docker files not built (no Docker)
- [x] CLI: `verify-integrity`, `verify-rls`, `catalogue-report --samples`, `send-test-email`
- [x] Docs final pass: README, CLAUDE.md, every doc matches the implementation
- [x] Production checklist walkthrough (mark what can and cannot be verified locally)
- [x] Delivery report (`docs/DELIVERY_REPORT.md`)

## Acceptance
All launch-readiness criteria in ACCEPTANCE_CRITERIA.md are Passed or explicitly Unverified with a
reason.

Progress notes (2026-10-15):
- Defects found and fixed during this phase: product facets returned 500 for searches
  (auto-correlated subquery; regression test added); product detail cached 60 s (stale stock);
  layout shift from the late announcement bar and short loading pages (CLS up to 0.96 → ≈0);
  `aria-label` on a plain `div` (loading grid); heading order on listings; missing assets would have
  been served as `index.html` with a one-year cache (Caddyfile).
- Launch-readiness status per criterion: FEATURE_MATRIX.md (L1–L21).
- Open items need the owner or real infrastructure: see PRODUCTION_CHECKLIST.md walkthrough.
