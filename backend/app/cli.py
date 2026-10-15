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


def _e2e_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", required=True, help="JSON file to write (must be git-ignored)")


E2E_ADMIN_EMAIL = "e2e-admin@example.com"


@command(
    "e2e-admin",
    "DEVELOPMENT ONLY: create/reset the end-to-end test admin with a new random password.",
    _e2e_args,
)
def e2e_admin(args: argparse.Namespace, settings: Settings) -> int:
    """Used by Playwright's global setup. The password is random on every run and written only to
    the given (git-ignored) file, so no admin password ever exists in the source code."""
    import json
    import secrets
    from pathlib import Path

    from sqlalchemy import select

    from app.core.security import hash_password
    from app.models import User
    from app.services.auth import revoke_all_sessions

    if settings.is_production:
        print("e2e-admin is disabled in production.")
        return 2
    password = secrets.token_urlsafe(24)
    with _session(settings) as db:
        user = db.scalar(select(User).where(User.email == E2E_ADMIN_EMAIL))
        if user is None:
            user = User(email=E2E_ADMIN_EMAIL, full_name="E2E Admin", role="admin")
            db.add(user)
        user.password_hash = hash_password(password)
        user.role = "admin"
        user.is_active = True
        db.flush()
        revoke_all_sessions(db, user.id, "e2e_reset")
        db.commit()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"email": E2E_ADMIN_EMAIL, "password": password}), encoding="utf-8")
    print(f"E2E admin ready ({E2E_ADMIN_EMAIL}); credentials written to {out}.")
    return 0


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


@command("run-jobs", "Run background jobs once now (expire/reconcile orders, send emails).")
def run_jobs(_args: argparse.Namespace, settings: Settings) -> int:
    from app.core.db import make_engine, make_session_factory
    from app.jobs import refresh_prices, run_once
    from app.services.payment_gateway import make_gateway

    factory = make_session_factory(make_engine(settings.database_url, pool_size=1, max_overflow=0))
    report = run_once(factory, settings, make_gateway(settings))
    refresh_prices(factory)
    print(
        f"Orders checked: {report.checked}, paid: {report.paid}, expired: {report.expired}, "
        f"review: {report.review}, provider errors: {report.errors}"
    )
    return 0


@command(
    "reconcile-payments",
    "Ask the payment provider about EVERY pending order now (not only overdue ones).",
)
def reconcile_payments(_args: argparse.Namespace, settings: Settings) -> int:
    from app.core.db import make_engine, make_session_factory
    from app.jobs import run_once
    from app.services.payment_gateway import make_gateway

    factory = make_session_factory(make_engine(settings.database_url, pool_size=1, max_overflow=0))
    report = run_once(factory, settings, make_gateway(settings), include_unexpired=True)
    print(
        f"Orders checked: {report.checked}, paid: {report.paid}, expired: {report.expired}, "
        f"review: {report.review}, provider errors: {report.errors}"
    )
    return 1 if report.errors else 0


# --------------------------------------------------------------------------------------------
# Operations checks (docs/operations/MONITORING.md)
# --------------------------------------------------------------------------------------------


def _print_problems(title: str, problems: list[object]) -> int:
    if not problems:
        print(f"{title}: OK")
        return 0
    print(f"{title}: {len(problems)} problem(s)")
    for problem in problems:
        print(f"  [{problem.check}] {problem.detail}")  # type: ignore[attr-defined]
    return 1


@command(
    "verify-integrity",
    "Check stock ledger, reservations, order totals, payments and refunds (read-only).",
)
def verify_integrity(_args: argparse.Namespace, settings: Settings) -> int:
    from app.services.ops_checks import integrity_problems

    with _session(settings) as db:
        return _print_problems("Integrity", list(integrity_problems(db)))


@command(
    "verify-rls",
    "Check that every table has row-level security on and no policies (Supabase safety).",
)
def verify_rls(_args: argparse.Namespace, settings: Settings) -> int:
    from app.services.ops_checks import rls_problems

    with _session(settings) as db:
        return _print_problems("Row-level security", list(rls_problems(db)))


def _catalogue_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--samples",
        action="store_true",
        help="Exit with an error while any SAMPLE product is still published (use before launch).",
    )


@command(
    "catalogue-report",
    "List what needs attention before launch: sample products, placeholder photos, gaps.",
    _catalogue_args,
)
def catalogue_report(args: argparse.Namespace, settings: Settings) -> int:
    from app.services.ops_checks import catalogue_report as build

    with _session(settings) as db:
        report = build(db)
    print(
        "Products by status: " + ", ".join(f"{k}={v}" for k, v in sorted(report.by_status.items()))
    )
    sections = [
        ("Published SAMPLE products (replace or archive before launch)", report.samples),
        ("Unpriced published products (missing gold rate or price)", report.unpriced),
        ("Published products with only placeholder pictures", report.placeholder_images),
        ("Published products without pictures", report.no_images),
        ("Published products without hallmark details", report.missing_hallmark),
    ]
    for title, slugs in sections:
        print(f"{title}: {len(slugs)}")
        for slug in slugs:
            print(f"  - {slug}")
    if report.unpriced or (args.samples and report.samples):
        return 1
    return 0


def _test_email_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--to", required=True, help="Recipient address (your own inbox).")


@command(
    "send-test-email",
    "Send one test message through the configured EMAIL_BACKEND and report the result.",
    _test_email_args,
)
def send_test_email(args: argparse.Namespace, settings: Settings) -> int:
    from sqlalchemy import select

    from app.core.time import utcnow
    from app.models import EmailOutbox
    from app.services import email as email_service

    key = f"test-email:{utcnow().isoformat()}"
    with _session(settings) as db:
        email_service.enqueue(
            db,
            key=key,
            to=args.to.strip(),
            template="test_email",
            subject=f"{settings.store_name}: test email",
            context={"sent_from": settings.email_from},
        )
        db.commit()
    email_service.dispatch_pending(lambda: _session(settings), settings)
    with _session(settings) as db:
        row = db.scalar(select(EmailOutbox).where(EmailOutbox.idempotency_key == key))
    if row is None:  # pragma: no cover - enqueue always inserts a new key
        print("The test email was not queued.")
        return 1
    print(f"Backend: {settings.email_backend}. Status: {row.status}.")
    if row.status == "sent":
        print("Handed to the SMTP server. Check the inbox (and spam folder).")
        return 0
    if row.status == "written_to_sink":
        print("Written to the development sink, NOT delivered (EMAIL_BACKEND is not smtp).")
        return 0
    print(f"Not sent yet: {row.last_error or 'see the email_outbox table'}")
    return 1


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
