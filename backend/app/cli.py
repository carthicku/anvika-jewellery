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
