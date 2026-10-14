"""Role/permission rules and the admin-route guard (docs/architecture/AUTHENTICATION.md §4)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import cli
from app.core.permissions import ROLE_PERMISSIONS, has_permission
from app.models import AuditLog, User


def _dependency_permissions(route: APIRoute) -> set[str]:
    found: set[str] = set()
    stack = list(route.dependant.dependencies)
    while stack:
        dep = stack.pop()
        permission = getattr(dep.call, "required_permission", None)
        if permission:
            found.add(permission)
        stack.extend(dep.dependencies)
    return found


def test_every_admin_route_declares_a_permission(app: FastAPI) -> None:
    admin_routes = [
        r for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/api/v1/admin")
    ]
    missing = [
        f"{sorted(r.methods)} {r.path}" for r in admin_routes if not _dependency_permissions(r)
    ]
    assert missing == [], f"Admin routes without require_permission(...): {missing}"


def test_guard_detects_an_unprotected_admin_route(app: FastAPI) -> None:
    @app.get("/api/v1/admin/_unprotected_probe")
    def probe() -> dict[str, str]:
        return {}

    with pytest.raises(AssertionError):
        test_every_admin_route_declares_a_permission(app)


def test_role_matrix() -> None:
    assert ROLE_PERMISSIONS["customer"] == frozenset()
    assert has_permission("staff", "orders:write")
    assert not has_permission("staff", "orders:refund")
    assert not has_permission("staff", "pricing:write")
    assert has_permission("admin", "users:manage")
    assert not has_permission("unknown-role", "dashboard:view")


@contextmanager
def _use_session(db: Session) -> Iterator[Session]:
    yield db


def test_create_admin_cli_prompts_for_password_and_audits(
    db: Session,
    settings,
    monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
) -> None:
    answers = iter(["owner passphrase 2026", "owner passphrase 2026"])
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": next(answers))
    monkeypatch.setattr(cli, "_session", lambda _settings: _use_session(db))
    assert cli.main(["create-admin", "--email", "Owner@Example.com", "--name", "Store Owner"]) == 0
    user = db.scalar(select(User).where(User.email == "owner@example.com"))
    assert user is not None and user.role == "admin" and user.password_hash.startswith("$argon2")
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "user.create_admin"))
    assert audit is not None and audit.entity_id == str(user.id)


def test_create_admin_rejects_weak_password(
    db: Session,
    settings,
    monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": "password")
    monkeypatch.setattr(cli, "_session", lambda _settings: _use_session(db))
    assert cli.main(["create-admin", "--email", "owner@example.com", "--name", "Owner"]) == 2
    assert db.scalar(select(User).where(User.email == "owner@example.com")) is None
