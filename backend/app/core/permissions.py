"""Fixed role → permission map (docs/architecture/AUTHENTICATION.md §4).

Kept in code, not in the database, so that no data edit can grant new powers. Every admin
endpoint declares the permission it needs with `Depends(require_permission("..."))`.
"""

from __future__ import annotations

from typing import Literal

Permission = Literal[
    "dashboard:view",
    "catalogue:write",
    "inventory:write",
    "orders:write",
    "orders:refund",
    "customers:view",
    "content:write",
    "promotions:write",
    "pricing:write",
    "settings:write",
    "audit:view",
    "users:manage",
]

_STAFF: frozenset[Permission] = frozenset(
    {
        "dashboard:view",
        "catalogue:write",
        "inventory:write",
        "orders:write",
        "customers:view",
        "content:write",
    }
)
_ADMIN: frozenset[Permission] = _STAFF | {
    "orders:refund",
    "promotions:write",
    "pricing:write",
    "settings:write",
    "audit:view",
    "users:manage",
}

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "customer": frozenset(),
    "staff": _STAFF,
    "admin": _ADMIN,
}


def has_permission(role: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def permissions_for(role: str) -> list[Permission]:
    return sorted(ROLE_PERMISSIONS.get(role, frozenset()))
