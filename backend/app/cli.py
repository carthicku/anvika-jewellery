"""Command-line tools:  .venv/Scripts/python -m app.cli <command> [options]

Run `python -m app.cli --help` to list commands. Each command explains itself with `--help`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, Settings, get_settings

Command = Callable[[argparse.Namespace, Settings], int]
COMMANDS: dict[str, tuple[Command, Callable[[argparse.ArgumentParser], None], str]] = {}


def command(
    name: str, help_text: str, configure: Callable[[argparse.ArgumentParser], None] | None = None
) -> Callable[[Command], Command]:
    def register(func: Command) -> Command:
        COMMANDS[name] = (func, configure or (lambda _p: None), help_text)
        return func

    return register


def _export_openapi_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        default=str(BACKEND_DIR / "openapi.json"),
        help="Where to write the schema (default: backend/openapi.json)",
    )


@command(
    "export-openapi",
    "Write the API contract (OpenAPI JSON) used to generate frontend types.",
    _export_openapi_args,
)
def export_openapi(args: argparse.Namespace, settings: Settings) -> int:
    from app.main import create_app

    app = create_app(settings)
    schema = app.openapi()
    output = Path(args.output)
    output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {output} ({len(schema.get('paths', {}))} paths)")
    return 0


def _session(settings: Settings) -> Session:
    from app.core.db import make_engine, make_session_factory

    return make_session_factory(make_engine(settings.database_url, pool_size=1, max_overflow=0))()


def _seed_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Required to seed when APP_ENV=production (you almost certainly should not).",
    )


@command(
    "seed",
    "Load the deterministic SAMPLE catalogue, rates, shipping and draft pages (idempotent).",
    _seed_args,
)
def seed(args: argparse.Namespace, settings: Settings) -> int:
    from app.seed import run_seed

    if settings.is_production and not args.allow_production:
        print("Refusing to load sample data into production (pass --allow-production to force).")
        return 2
    with _session(settings) as db:
        summary = run_seed(db)
        db.commit()
    print("Seeded: " + ", ".join(f"{k}={v}" for k, v in summary.items()))
    return 0


@command("refresh-prices", "Recompute the listing price cache (products.price_from).")
def refresh_prices(_args: argparse.Namespace, settings: Settings) -> int:
    from app.services.catalogue import refresh_price_cache

    with _session(settings) as db:
        count = refresh_price_cache(db)
        db.commit()
    print(f"Refreshed listing prices for {count} products.")
    return 0


def _prompt_password(email: str) -> str | None:
    import getpass

    from app.core.security import password_problems

    first = getpass.getpass("Password (not shown): ")
    problems = password_problems(first, email)
    if problems:
        print("Password rejected: " + " ".join(problems))
        return None
    if getpass.getpass("Repeat password: ") != first:
        print("Passwords do not match.")
        return None
    return first


def _user_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True, help="Full name, in quotes if it has spaces")


def _create_user(settings: Settings, email: str, name: str, role: str) -> int:
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.core.time import utcnow
    from app.models import User
    from app.services import audit

    address = email.strip().lower()
    password = _prompt_password(address)
    if password is None:
        return 2
    with _session(settings) as db:
        if db.scalar(select(User).where(User.email == address)):
            print(f"A user with email {address} already exists. Nothing changed.")
            return 2
        user = User(
            email=address,
            password_hash=hash_password(password),
            full_name=name.strip(),
            role=role,
            email_verified_at=utcnow(),
        )
        db.add(user)
        db.flush()
        audit.record(
            db,
            actor=None,
            action=f"user.create_{role}",
            entity_type="user",
            entity_id=user.id,
            changes={"email": address, "role": role, "source": "cli"},
        )
        db.commit()
    print(f"Created {role} account for {address}.")
    return 0


@command(
    "create-admin",
    "Create an administrator account (password is prompted, never passed as an argument).",
    _user_args,
)
def create_admin(args: argparse.Namespace, settings: Settings) -> int:
    return _create_user(settings, args.email, args.name, "admin")


@command(
    "create-customer",
    "DEVELOPMENT ONLY: create a customer account (password prompted).",
    _user_args,
)
def create_customer(args: argparse.Namespace, settings: Settings) -> int:
    if settings.is_production:
        print("create-customer is disabled in production; customers register on the website.")
        return 2
    return _create_user(settings, args.email, args.name, "customer")


def _email_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--email", required=True)


@command(
    "deactivate-user",
    "Deactivate an account and sign it out everywhere immediately (e.g. compromised staff).",
    _email_arg,
)
def deactivate_user(args: argparse.Namespace, settings: Settings) -> int:
    from sqlalchemy import select

    from app.models import User
    from app.services import audit
    from app.services.auth import revoke_all_sessions

    with _session(settings) as db:
        user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if user is None:
            print("No such user.")
            return 2
        user.is_active = False
        revoke_all_sessions(db, user.id, "deactivated")
        audit.record(
            db,
            actor=None,
            action="user.deactivate",
            entity_type="user",
            entity_id=user.id,
            changes={"source": "cli"},
        )
        db.commit()
    print(f"Deactivated {user.email} and revoked all sessions.")
    return 0


@command("run-jobs", "Run background jobs once now (send pending emails).")
def run_jobs(_args: argparse.Namespace, settings: Settings) -> int:
    from app.core.db import make_engine, make_session_factory
    from app.services import email as email_service

    factory = make_session_factory(make_engine(settings.database_url, pool_size=1, max_overflow=0))
    sent = email_service.dispatch_pending(factory, settings)
    print(f"Emails processed: {sent}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_func, configure, help_text) in sorted(COMMANDS.items()):
        configure(sub.add_parser(name, help=help_text, description=help_text))
    args = parser.parse_args(argv)
    func = COMMANDS[args.command][0]
    return func(args, get_settings())


if __name__ == "__main__":
    sys.exit(main())
