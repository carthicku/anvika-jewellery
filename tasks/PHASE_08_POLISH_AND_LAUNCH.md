# Phase 8 — Quality and Launch Preparation

Goal: an evidence-based deployment-ready candidate with remaining external dependencies listed.

## Tasks
- [ ] Complete the E2E suite J1–J12 (desktop + mobile projects) + route smoke test + axe scans
- [ ] Manual keyboard pass and responsive pass (recorded)
- [ ] Security review against SECURITY_MODEL (record evidence per control); `pip-audit`, `npm audit`
- [ ] SEO: titles/descriptions, canonical, OG, Product JSON-LD (verified fields only), robots.txt,
      sitemap, `noindex` for private routes
- [ ] Performance: bundle analysis, image sizes, Lighthouse runs recorded; API query EXPLAIN checks
- [ ] Deployment files: backend Dockerfile, `deploy/docker-compose.prod.yml`, `deploy/Caddyfile`
      (headers, CSP, caching)
- [ ] CLI: `verify-integrity`, `verify-rls`, `catalogue-report --samples`, `send-test-email`
- [ ] Docs final pass: README, CLAUDE.md, every doc matches the implementation
- [ ] Production checklist walkthrough (mark what can and cannot be verified locally)
- [ ] Delivery report

## Acceptance
All launch-readiness criteria in ACCEPTANCE_CRITERIA.md are Passed or explicitly Unverified with a
reason.
