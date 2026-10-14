"""Logging setup: readable text in development, one JSON object per line in production.

Sensitive values are redacted before they are written. See docs/architecture/SECURITY_MODEL.md §4.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import get_request_id, get_user_id

_SENSITIVE_KEY = re.compile(
    r"pass(word)?|secret|token|authorization|cookie|signature|api[_-]?key|card|cvv|otp",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"
# Attributes present on every LogRecord; anything else was passed via `extra=`.
_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}


def redact(value: Any) -> Any:
    """Recursively replace values of sensitive-looking keys."""
    if isinstance(value, dict):
        return {
            k: (_REDACTED if _SENSITIVE_KEY.search(str(k)) else redact(v)) for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.user_id = get_user_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
        }
        extras = {k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS}
        extras.pop("request_id", None)
        extras.pop("user_id", None)
        payload.update(redact(extras))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS}
        rid = extras.pop("request_id", None)
        extras.pop("user_id", None)
        suffix = " ".join(f"{k}={v}" for k, v in redact(extras).items())
        prefix = f"[{rid[:8]}] " if rid else ""
        return f"{prefix}{base}{(' ' + suffix) if suffix else ''}"


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # Our access log replaces uvicorn's (which would log full URLs incl. query strings).
    logging.getLogger("uvicorn.access").disabled = True
