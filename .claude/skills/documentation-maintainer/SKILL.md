---
name: documentation-maintainer
description: Use at the end of every meaningful change or checkpoint, or when commands, environment variables, API routes, schema, behaviour or project status change. Keeps CLAUDE.md, README, docs/ and tasks/ synchronised with the code, and records checkpoints and known limitations accurately.
---

# Documentation maintainer

## What to update when…
| Change | Update |
|--------|--------|
| New/changed env var | `docs/development/ENVIRONMENT_VARIABLES.md`, `backend/.env.example` or `frontend/.env.example` |
| New/changed command or script | `README.md` quick start, `docs/development/LOCAL_SETUP.md`, `CLAUDE.md` commands section |
| Schema change | `docs/architecture/DATABASE_SCHEMA.md`, `ER_DIAGRAM.md` |
| Route added/removed | `docs/architecture/API_CONTRACT.md` (+ regenerate `openapi.json`) |
| Business rule change | Matching architecture doc (PRICING_ENGINE, PAYMENT_FLOW, INVENTORY_AND_ORDERS, AUTHENTICATION) |
| Significant decision | New ADR + `docs/ASSUMPTIONS_AND_DECISIONS.md` |
| Task finished (verified) | Tick it in `tasks/PHASE_0N_*.md`; update `tasks/MASTER_TASKS.md` phase status |
| Feature verified | `docs/FEATURE_MATRIX.md` status + evidence (test name) |
| Tests run at a checkpoint | Dated entry in `docs/quality/TEST_RESULTS.md` |
| Limitation found / removed | `docs/quality/KNOWN_LIMITATIONS.md` |
| Any checkpoint | `PROJECT_STATUS.md` (current phase, what works, blockers, next step, how to resume) and `CHANGELOG.md` |

## Rules
* Documentation describes **what exists**. Mark plans as plans ("planned", "not yet verified").
* Never mark something done/verified without evidence.
* Keep docs concise. Delete outdated statements rather than adding contradictions.
* Relative links between docs must resolve. Check with
  `py -3.13 scripts/check_docs.py` (verifies required files exist, Markdown links resolve and skill
  frontmatter is valid).
* Beginner-friendly: when documenting a command, say what it does in one plain sentence.
