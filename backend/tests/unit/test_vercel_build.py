"""The Vercel build hook must never touch a database unless explicitly asked to, on previews."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import vercel_build

used_urls: list[str] = []


@pytest.fixture()
def commands(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    ran: list[list[str]] = []
    used_urls.clear()

    def fake_run(
        command: list[str], check: bool = False, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        ran.append(command)
        used_urls.append((env or {}).get("DATABASE_URL", ""))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(vercel_build.subprocess, "run", fake_run)
    for name in ("SETUP_DB_ON_BUILD", "VERCEL_ENV", "APP_ENV", "DATABASE_URL_DIRECT"):
        monkeypatch.delenv(name, raising=False)
    return ran


def test_does_nothing_by_default(commands: list[list[str]]) -> None:
    assert vercel_build.main() == 0
    assert commands == []


def test_never_runs_on_production_builds(
    commands: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SETUP_DB_ON_BUILD", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")
    assert vercel_build.main() == 0
    assert commands == []
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("APP_ENV", "production")
    assert vercel_build.main() == 0
    assert commands == []


def test_runs_migrations_then_seed_on_an_opted_in_preview(
    commands: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SETUP_DB_ON_BUILD", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    assert vercel_build.main() == 0
    assert [c[1:] for c in commands] == [
        ["-m", "alembic", "upgrade", "head"],
        ["-m", "app.cli", "seed"],
    ]
    assert Path(vercel_build.__file__).name == "vercel_build.py"


def test_prefers_the_direct_connection_for_schema_changes(
    commands: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SETUP_DB_ON_BUILD", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://pooled")
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgresql+psycopg://direct")
    vercel_build.main()
    assert used_urls == ["postgresql+psycopg://direct"] * 2
