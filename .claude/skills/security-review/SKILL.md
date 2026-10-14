---
name: security-review
description: Use when reviewing authentication, authorization, input handling, secrets, file uploads, payment handling, logging, CORS/CSRF/cookies, security headers or deployment configuration of the jewellery store, or before any release. Finds exploitable issues, implements fixes, and records evidence in SECURITY_REVIEW.md.
---

# Security review

Threat model: `docs/architecture/SECURITY_MODEL.md` (23 numbered controls). Record results in
`docs/quality/SECURITY_REVIEW.md`.

## Procedure
1. Scope the review (files/changes). For a release, cover all 23 controls.
2. For each control in scope, **find the code** that implements it and **the test** that proves it.
   Mark the control verified only when both exist and the test passed in this session.
3. Hunt actively:
   - Grep for risky patterns: `text(`/f-strings in SQL, `float(`, `dangerouslySetInnerHTML`,
     `localStorage` with tokens, `print(`/`logger.*(password|token|secret)`, `allow_origins=["*"]`,
     `verify=False`, `VITE_.*(SECRET|KEY)` (other than public ids), `# noqa`/`type: ignore` near
     security code.
   - For each endpoint: who can call it? Does it check ownership? What if the ids are someone else's?
     What if the request is replayed or sent concurrently?
   - Uploads: type allow-list, size limit, decode + re-encode, random names.
   - Secrets: `python scripts/check-secrets.py`; `.gitignore` covers `.env*`.
   - Dependencies: `pip-audit -r backend/requirements.txt`, `npm audit --omit=dev` in `frontend/`.
4. **Fix** confirmed issues with a regression test. Propose larger changes as tasks.
5. **Record**: date, scope, findings (severity, location, fix/status), and the updated control table.

## Never
* Claim an audit is "complete" or "secure" without listing what was checked and the evidence.
* Disable a security control to make a test or feature work.
* Put real secrets in code, tests, docs, commit messages or chat output.
