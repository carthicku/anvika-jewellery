"""Command-line tools:  .venv/Scripts/python -m app.cli <command> [options]

Run `python -m app.cli --help` to list commands. Each command explains itself with `--help`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

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
