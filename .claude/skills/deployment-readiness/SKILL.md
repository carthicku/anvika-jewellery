---
name: deployment-readiness
description: Use before any staging or production deployment, or when asked whether the store is ready to launch. Verifies builds, tests, migrations, environment configuration, production security settings, and payment/email/shipping readiness, and produces an evidence-based launch checklist with blockers.
---

# Deployment readiness

Sources: `docs/operations/PRODUCTION_CHECKLIST.md`, `docs/operations/DEPLOYMENT.md`,
`docs/ACCEPTANCE_CRITERIA.md` (L1–L21).

## Procedure
1. **Build & test** (record the output):
   - `scripts/check.ps1` (or `.sh`): lint, types, unit and API tests
   - `cd frontend && npm run build` (note the bundle sizes)
   - `cd frontend && npm run e2e` against a seeded environment
2. **Migrations**: on a fresh DB, `alembic upgrade head`, then `alembic check` (no drift). Confirm a
   backup exists before migrating the target environment.
3. **Configuration**: start the backend with `APP_ENV=production` and the target env file. It must
   refuse the simulator, missing or weak secrets, and insecure cookies. Verify `ALLOWED_ORIGINS`,
   `PUBLIC_SITE_URL`, `COOKIE_SECURE`, `TRUSTED_PROXY_COUNT`.
4. **Security**: run the `security-review` skill procedure; secrets scan; dependency audits; headers
   and CSP (`curl -I`); RLS check (`python -m app.cli verify-rls`).
5. **Integrations**:
   - Razorpay: keys match the mode (test/live); webhook configured and a test delivery returns 200;
     one end-to-end payment + refund in that mode.
   - Email: `send-test-email` arrives in the inbox; SPF/DKIM/DMARC pass.
   - Shipping: methods, fees and zones configured.
   - Storage: an upload works and the image URL loads over HTTPS.
6. **Business readiness**: sample data removed, real gold rates, policies approved, GST confirmed
   (owner items in the checklist).
7. **Report** a table of each checklist item → ✅ verified (evidence) / ❌ failing / ⏳ blocked
   (owner/external) / ❔ unverified, with the overall recommendation. **Never declare "ready" or
   "live" while any blocker remains or without having observed the deployed site working.**
