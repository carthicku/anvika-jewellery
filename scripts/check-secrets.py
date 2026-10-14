"""Scan files tracked by Git (plus staged/untracked, non-ignored files) for likely secrets.

Usage (repository root):  py -3.13 scripts/check-secrets.py
Exit code 1 if anything suspicious is found. This is a safety net, not a replacement for care:
real secrets belong only in git-ignored .env files and the hosting provider's secret store.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Razorpay live key", re.compile(r"rzp_live_[A-Za-z0-9]{8,}")),
    ("Razorpay test key id with secret nearby", re.compile(r"rzp_test_[A-Za-z0-9]{10,}")),
    ("Private key block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Supabase service/anon JWT", re.compile(r"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9_-]{20,}")),
    ("Postgres URL with real password",
     re.compile(r"postgres(?:ql)?(?:\+psycopg)?://[^:\s]+:(?!postgres@|<password>|PASSWORD|password@)[^@\s]{6,}@(?!127\.0\.0\.1|localhost|db:)")),
    ("Assigned secret value",
     re.compile(r"(?i)^(?:\s*)(SECRET_KEY|RAZORPAY_KEY_SECRET|RAZORPAY_WEBHOOK_SECRET|SMTP_PASSWORD|S3_SECRET_ACCESS_KEY)\s*=\s*[^\s<#]{8,}")),
]

ALLOWLIST_FILES = {"scripts/check-secrets.py"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".woff", ".woff2", ".ico", ".lock"}


def candidate_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [ROOT / line for line in out.splitlines() if line.strip()]


def main() -> int:
    findings: list[str] = []
    for path in candidate_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWLIST_FILES or path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append(f"{rel}:{lineno}: {label}")
    if findings:
        print("Possible secrets found (move them to a git-ignored .env file):")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("OK: no likely secrets found in tracked or untracked (non-ignored) files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
