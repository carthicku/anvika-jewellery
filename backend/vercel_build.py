"""Optional database set-up while Vercel builds a PREVIEW deployment (demo previews only).

Vercel's build machines can reach the database, so a preview can create its own tables and sample
catalogue without anyone running commands against it by hand. It runs only when ALL of these hold:
  * SETUP_DB_ON_BUILD=1 is set for the Preview environment,
  * the build is a preview (VERCEL_ENV=preview) — never production,
  * the app is not in production mode.
If DATABASE_URL_DIRECT is set (a non-pooled connection string) the set-up uses it instead of the
pooled DATABASE_URL, because schema changes should not go through a transaction-mode pooler.
It runs the same Alembic migrations and idempotent sample seed as the documented commands, then
creates a demo admin if PREVIEW_ADMIN_EMAIL and PREVIEW_ADMIN_PASSWORD are set (Preview
variables). Real stores should run migrations themselves (docs/operations/DEPLOYMENT.md §7).
"""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    if os.environ.get("SETUP_DB_ON_BUILD") != "1":
        print("vercel_build: SETUP_DB_ON_BUILD is not set; nothing to do.")
        return 0
    if os.environ.get("VERCEL_ENV") != "preview" or os.environ.get("APP_ENV") == "production":
        print("vercel_build: refusing to touch the database outside a preview build.")
        return 0
    env = dict(os.environ)
    if env.get("DATABASE_URL_DIRECT"):
        env["DATABASE_URL"] = env["DATABASE_URL_DIRECT"]
    for command in (
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [sys.executable, "-m", "app.cli", "seed"],
        [sys.executable, "-m", "app.cli", "create-preview-admin"],  # no-op without the variables
    ):
        print("vercel_build: running", " ".join(command[1:]))
        result = subprocess.run(command, check=False, env=env)  # noqa: S603
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
