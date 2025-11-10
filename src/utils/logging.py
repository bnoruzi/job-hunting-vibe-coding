"""Structured logging helpers for application modules."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator

_DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_RESERVED_LOG_RECORD_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}

_LOGGING_INITIALIZED = False


def _stringify(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        json.dumps(value)
    except TypeError:
        return repr(value)
    return value


class _JsonFormatter(logging.Formatter):
    """Formatter that emits structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - delegated to stdlib
        log: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_KEYS or key.startswith("_"):
                continue
            log[key] = _stringify(value)

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log["stack"] = record.stack_info

        return json.dumps(log, default=_stringify)


def setup_logging(level: str | int = _DEFAULT_LOG_LEVEL) -> None:
    """Configure global logging to emit structured JSON records once."""

    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return

    log_level = logging.getLevelName(level)
    if isinstance(log_level, str):  # unknown level names return string representation
        log_level = logging.INFO

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)

    _LOGGING_INITIALIZED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a module-specific logger configured for structured logging."""

    setup_logging()
    return logging.getLogger(name)


@contextmanager
def log_latency(logger: logging.Logger, event: str, **context: Any) -> Iterator[None]:
    """Context manager that logs latency and failures for wrapped calls."""

    normalized_context = {key: _stringify(value) for key, value in context.items()}
    start = time.perf_counter()
    try:
        yield
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            event,
            extra={
                **normalized_context,
                "event": event,
                "status": "error",
                "duration_ms": duration_ms,
            },
        )
        raise
    else:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            event,
            extra={
                **normalized_context,
                "event": event,
                "status": "ok",
                "duration_ms": duration_ms,
            },
        )
