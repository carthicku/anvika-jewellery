"""Check that required documentation exists, Markdown links resolve, and skills are well-formed.

Usage (from the repository root):
    py -3.13 scripts/check_docs.py

Exits with status 1 and prints every problem found; prints a summary and exits 0 otherwise.
Standard library only, so it runs before any dependencies are installed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "CLAUDE.md",
    "README.md",
    "PROJECT_STATUS.md",
    "IMPLEMENTATION_PLAN.md",
    "CHANGELOG.md",
    ".env.example",
    "docs/PRODUCT_REQUIREMENTS.md",
    "docs/USER_JOURNEYS.md",
    "docs/FEATURE_MATRIX.md",
    "docs/ACCEPTANCE_CRITERIA.md",
    "docs/ASSUMPTIONS_AND_DECISIONS.md",
    "docs/design/DESIGN_SYSTEM.md",
    "docs/design/COMPONENT_LIBRARY.md",
    "docs/design/RESPONSIVE_GUIDELINES.md",
    "docs/design/ACCESSIBILITY.md",
    "docs/architecture/SYSTEM_ARCHITECTURE.md",
    "docs/architecture/DATABASE_SCHEMA.md",
    "docs/architecture/ER_DIAGRAM.md",
    "docs/architecture/API_CONTRACT.md",
    "docs/architecture/AUTHENTICATION.md",
    "docs/architecture/PRICING_ENGINE.md",
    "docs/architecture/PAYMENT_FLOW.md",
    "docs/architecture/INVENTORY_AND_ORDERS.md",
    "docs/architecture/SECURITY_MODEL.md",
    "docs/architecture/ADR/README.md",
    "docs/development/LOCAL_SETUP.md",
    "docs/development/ENVIRONMENT_VARIABLES.md",
    "docs/development/DATABASE_MIGRATIONS.md",
    "docs/development/SEED_DATA.md",
    "docs/development/TESTING.md",
    "docs/development/CODE_CONVENTIONS.md",
    "docs/development/COMMON_ERRORS.md",
    "docs/operations/DEPLOYMENT.md",
    "docs/operations/BACKUP_AND_RESTORE.md",
    "docs/operations/MONITORING.md",
    "docs/operations/INCIDENT_RESPONSE.md",
    "docs/operations/PRODUCTION_CHECKLIST.md",
    "docs/operations/PAYMENT_PROVIDER_SETUP.md",
    "docs/operations/EMAIL_SETUP.md",
    "docs/operations/SHIPPING_SETUP.md",
    "docs/quality/TEST_PLAN.md",
    "docs/quality/TEST_RESULTS.md",
    "docs/quality/SECURITY_REVIEW.md",
    "docs/quality/PERFORMANCE_REVIEW.md",
    "docs/quality/KNOWN_LIMITATIONS.md",
    "tasks/MASTER_TASKS.md",
    "tasks/PHASE_01_FOUNDATION.md",
    "tasks/PHASE_02_DESIGN_SYSTEM.md",
    "tasks/PHASE_03_CATALOGUE.md",
    "tasks/PHASE_04_AUTH_AND_ACCOUNTS.md",
    "tasks/PHASE_05_CART_AND_CHECKOUT.md",
    "tasks/PHASE_06_PAYMENTS_AND_ORDERS.md",
    "tasks/PHASE_07_ADMIN_AND_INVENTORY.md",
    "tasks/PHASE_08_POLISH_AND_LAUNCH.md",
]

REQUIRED_SKILLS = [
    "project-architecture",
    "premium-ui-ux",
    "react-frontend",
    "fastapi-backend",
    "gold-pricing-engine",
    "secure-payments-and-orders",
    "inventory-management",
    "testing-and-qa",
    "security-review",
    "documentation-maintainer",
    "deployment-readiness",
]

SKIP_DIRS = {"node_modules", ".venv", ".git", "dist", ".localdb", "var"}
# [text](target) — ignores images' leading "!" by matching it optionally and skipping later.
LINK_RE = re.compile(r"(!?)\[[^\]]*\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def markdown_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return sorted(files)


def check_required(problems: list[str]) -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"missing required file: {rel}")
        elif path.stat().st_size < 40:
            problems.append(f"required file is (nearly) empty: {rel}")


def check_links(problems: list[str]) -> int:
    count = 0
    for md in markdown_files():
        text = FENCE_RE.sub("", md.read_text(encoding="utf-8"))
        for _bang, target in LINK_RE.findall(text):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue  # external URL, mailto:, or in-page anchor
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            count += 1
            resolved = (md.parent / target_path).resolve()
            if not resolved.exists():
                problems.append(f"broken link in {md.relative_to(ROOT)}: {target}")
    return count


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def check_skills(problems: list[str]) -> None:
    skills_dir = ROOT / ".claude" / "skills"
    present = {p.name for p in skills_dir.iterdir() if p.is_dir()} if skills_dir.is_dir() else set()
    for name in sorted(set(REQUIRED_SKILLS) | present):
        skill_file = skills_dir / name / "SKILL.md"
        if not skill_file.is_file():
            problems.append(f"missing skill: .claude/skills/{name}/SKILL.md")
            continue
        fm = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        if fm is None:
            problems.append(f"skill {name}: missing or malformed YAML frontmatter")
            continue
        if fm.get("name") != name:
            problems.append(f"skill {name}: frontmatter name {fm.get('name')!r} != directory name")
        if not SKILL_NAME_RE.match(fm.get("name", "")) or len(fm.get("name", "")) > 64:
            problems.append(f"skill {name}: name must be lowercase-hyphenated, <= 64 chars")
        description = fm.get("description", "")
        if not description:
            problems.append(f"skill {name}: description is required")
        elif len(description) > 1024:
            problems.append(f"skill {name}: description longer than 1024 characters")


def main() -> int:
    problems: list[str] = []
    check_required(problems)
    link_count = check_links(problems)
    check_skills(problems)
    if problems:
        print(f"{len(problems)} problem(s) found:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(
        f"OK: {len(REQUIRED_FILES)} required files present, {link_count} relative links resolve, "
        f"{len(REQUIRED_SKILLS)} skills valid."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
