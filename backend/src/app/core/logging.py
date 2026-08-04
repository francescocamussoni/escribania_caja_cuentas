from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "access_token",
        "token",
        "authorization",
        "secret",
        "jwt",
    }
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload.update(_sanitize_context(context))
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _sanitize_context(context: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in context.items():
        if key.lower() in SENSITIVE_KEYS:
            continue
        sanitized[key] = value
    return sanitized


def log_security_event(logger: logging.Logger, event: str, **context: Any) -> None:
    logger.info(event, extra={"context": _sanitize_context({"event": event, **context})})
