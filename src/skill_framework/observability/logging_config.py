"""Centralized logging configuration with structured logging support."""

import logging
import logging.config
import os
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

_log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


class ContextualFormatter(logging.Formatter):
    """Formatter that includes contextual information in log records."""

    def format(self, record: logging.LogRecord) -> str:
        context = _log_context.get()
        for key, value in context.items():
            setattr(record, key, value)
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime

        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        context = _log_context.get()
        if context:
            log_data["context"] = context

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    log_file: Optional[str] = None,
) -> None:
    """
    Setup centralized logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ('json' or 'text')
        log_file: Optional file path for logging to file
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: Dict[str, Dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "level": log_level,
        }
    }

    if format_type == "json":
        handlers["console"]["formatter"] = "json"
    else:
        handlers["console"]["formatter"] = "detailed"

    if log_file:
        handlers["file"] = {
            "class": "logging.FileHandler",
            "filename": log_file,
            "level": log_level,
            "formatter": "json" if format_type == "json" else "detailed",
        }

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "detailed": {
                "()": ContextualFormatter,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": handlers,
        "root": {
            "level": log_level,
            "handlers": list(handlers.keys()),
        },
        "loggers": {
            "skill_framework": {
                "level": log_level,
                "handlers": list(handlers.keys()),
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def add_context(**kwargs: Any) -> None:
    """
    Add contextual fields to all subsequent log messages in this context.

    Args:
        **kwargs: Key-value pairs to add to log context
    """
    current_context = _log_context.get().copy()
    current_context.update(kwargs)
    _log_context.set(current_context)


def clear_context() -> None:
    """Clear all contextual fields."""
    _log_context.set({})


def get_context() -> Dict[str, Any]:
    """Get current log context."""
    return _log_context.get().copy()


def configure_from_env() -> None:
    """Configure logging from environment variables."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_format = os.getenv("LOG_FORMAT", "json")
    log_file = os.getenv("LOG_FILE")

    setup_logging(level=log_level, format_type=log_format, log_file=log_file)
