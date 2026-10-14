# Test Results

Append a dated entry after each verified checkpoint. Record the real command, counts and failures.
Never record a result that was not actually observed.

## Format
```
### YYYY-MM-DD — <checkpoint name>
| Suite | Command | Result |
|-------|---------|--------|
| Backend | `pytest` | 123 passed, 0 failed, 2 skipped (reason) |
Notes / failures / follow-ups.
```

---

### 2026-10-14 — Phase 0 (planning)
No application code exists yet, so no tests have been run. Environment checks performed:
| Check | Result |
|-------|--------|
| Node.js | v24.20.0 |
| npm | 11.19.0 |
| Python | 3.13.15 via `py -3.13` (Python 3.12 registration is broken on this machine) |
| Git | 2.56.0 |
| Docker / psql | not installed |
| Embedded PostgreSQL probe | `embedded-postgres@17.10.0-beta.17` started PostgreSQL 17.10 on Windows and answered `select version()` |

### 2026-10-14 — Phase 0 checkpoint
| Suite | Command | Result |
|-------|---------|--------|
| Docs & skills consistency | `py -3.13 scripts/check_docs.py` | OK: 54 required files present, 91 relative links resolve, 11 skills valid |
| Checker self-test | planted a broken link and a malformed skill | Both reported, exit code 1 |
