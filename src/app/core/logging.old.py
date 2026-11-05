"""
Logging Configuration
=====================

https://docs.python.org/3/library/logging.html#logrecord-attributes

Handlers
--------
- console: stdout, default format (dev only)
- web_console: stdout, request format with correlation_id (dev + FastAPI only)
- file_watcher: file, default format
- web_file_watcher: file, request format with correlation_id (FastAPI only)

Two handlers write to the same file intentionally:
- file_watcher uses the default format for infrastructure loggers (uvicorn, celery, etc.)
- web_file_watcher uses the request format (with correlation_id) for web route loggers. Append-mode writes on Linux are atomic, so concurrent writes are safe.

Process Types
-------------
Controlled via the PROCESS_TYPE environment variable (see config.ProcessType).
Defaults to FASTAPI if not set.

- FASTAPI: loads web handlers, correlation_id filter, and FastAPI/uvicorn loggers.
- CELERY_WORKER / CELERY_BEAT: loads file_watcher only, no correlation_id filter. asgi_correlation_id is NOT imported or instantiated in these processes.

Logger Propagation
------------------
All loggers set propagate=False, meaning log records do NOT travel up to the root logger.
Each logger is fully self-contained. As a result:

- The root logger is intentionally omitted from this config.
- This allows pytest to retain control of the root logger during testing, preserving its log capture behaviour (log_cli, log_cli_level, etc.).
- Any logger not explicitly configured here will fall through to whatever owns the root logger (pytest during tests, the default handler in production).

pytest Logging
--------------
- pytest will only capture logs from loggers that propagate to the root logger.
- Named loggers with propagate=False are self-contained and invisible to pytest, even if pytest sets the root logger to DEBUG. The root logger's level has no effect on named
  loggers — each logger filters records independently based on its own configured level before propagation is even considered.
- To expose a named logger to pytest, set propagate=True and remove its handlers, allowing records to bubble up to pytest's root handler. Logger levels can then be
  controlled via pyproject.toml log_levels or programmatically via logging.getLogger("name").setLevel() in a session fixture.
"""

from pathlib import Path
from typing import Any, Dict

from config import ProcessType, get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Filters, formatters, handlers
# ---------------------------------------------------------------------------


def _build_filters(is_fastapi: bool) -> Dict[str, Any]:
    """
    asgi_correlation_id is only imported/instantiated for FastAPI processes.
    dictConfig() eagerly constructs all filters in the dict, so we must
    exclude it entirely from non-FastAPI configs to avoid import errors.
    """
    if not is_fastapi:
        return {}
    return {
        "correlation_id": {
            "()": "asgi_correlation_id.CorrelationIdFilter",
            "uuid_length": 8,
            "default_value": "-",
        }
    }


def _build_formatters() -> Dict[str, Any]:
    default_fmt = "%(levelname)s : %(asctime)s.%(msecs)03d : %(processName)s[%(process)s] : %(name)s : %(message)s"
    web_request_fmt = "%(levelname)s : %(asctime)s.%(msecs)03d : %(processName)s[%(process)s] : %(name)s : %(correlation_id)s : %(message)s"
    celery_task_fmt = "%(levelname)s : %(asctime)s.%(msecs)03d : %(processName)s[%(process)s] : %(name)s : %(task)s[%(task_id)s] : %(message)s"
    return {
        "default": {"format": default_fmt, "datefmt": "%Y-%m-%d %H:%M:%S"},
        "requests": {"format": web_request_fmt, "datefmt": "%Y-%m-%d %H:%M:%S"},
        "tasks": {"format": celery_task_fmt, "datefmt": "%Y-%m-%d %H:%M:%S"},
    }


def _build_handlers(filename: Path, is_fastapi: bool, is_dev: bool) -> Dict[str, Any]:
    """
    All handler definitions live here. Only handlers relevant to the current
    process type and environment are selected into the returned dict.
    """
    all_handlers: Dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file_watcher": {
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "default",
            "filename": filename,
            "encoding": "utf8",
            "mode": "a",
        },
        "web_console": {
            "class": "logging.StreamHandler",
            "formatter": "requests",
            "filters": ["correlation_id"],
            "stream": "ext://sys.stdout",
        },
        "web_file_watcher": {
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "requests",
            "filename": filename,
            "filters": ["correlation_id"],
            "encoding": "utf8",
            "mode": "a",
        },
        "task_console": {
            "class": "logging.StreamHandler",
            "formatter": "tasks",
            "stream": "ext://sys.stdout",
        },
        "task_file_watcher": {
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "tasks",
            "filename": filename,
            "encoding": "utf8",
            "mode": "a",
        },
    }

    handlers: Dict[str, Any] = {}
    handlers["file_watcher"] = all_handlers["file_watcher"]

    if is_fastapi:
        handlers["web_file_watcher"] = all_handlers["web_file_watcher"]

    if is_dev:
        handlers["console"] = all_handlers["console"]
        if is_fastapi:
            handlers["web_console"] = all_handlers["web_console"]

    return handlers


# ---------------------------------------------------------------------------
# Logger builders
# ---------------------------------------------------------------------------


def _build_fastapi_loggers(log_level: str, file_h: list[str], web_h: list[str]) -> Dict[str, Any]:
    return {
        # Infrastructure
        "uvicorn": {"level": "WARNING", "handlers": file_h, "propagate": False},
        "uvicorn.access": {"level": "WARNING", "handlers": file_h, "propagate": False},
        "uvicorn.error": {"level": "WARNING", "handlers": file_h, "propagate": False},
        "gunicorn": {"level": "WARNING", "handlers": file_h, "propagate": False},
        "fastapi": {"level": "WARNING", "handlers": file_h, "propagate": False},
        # FastAPI Backend App (infrastructure loggers without correlation_id)
        "core.utils": {"level": "INFO", "handlers": file_h, "propagate": False},
        "api.startup": {"level": "INFO", "handlers": file_h, "propagate": False},
        # FastAPI Backend App (web handlers with correlation_id)
        "api.routing": {"level": "INFO", "handlers": web_h, "propagate": False},
        "api.middleware": {"level": "INFO", "handlers": web_h, "propagate": False},
        # FastAPI Routes & Services (web handlers with correlation_id)
        "core.exceptions": {"level": log_level, "handlers": web_h, "propagate": False},
        "core.db": {"level": log_level, "handlers": web_h, "propagate": False},
        "admin.routes": {"level": "INFO", "handlers": web_h, "propagate": False},
        "models.validators": {"level": log_level, "handlers": web_h, "propagate": False},
        "killteam.validators": {"level": log_level, "handlers": web_h, "propagate": False},
    }


def _build_celery_loggers(log_level: str, file_h: list[str]) -> Dict[str, Any]:
    return {
        # Infrastructure
        "celery": {"level": log_level, "handlers": file_h, "propagate": False},
        "celery.beat": {"level": log_level, "handlers": file_h, "propagate": False},
        "celery.app.trace": {"level": log_level, "handlers": file_h, "propagate": False},
        "celery.worker": {"level": log_level, "handlers": file_h, "propagate": False},
        "celery.worker.strategy": {"level": log_level, "handlers": file_h, "propagate": False},
        "celery.worker.consumer": {"level": log_level, "handlers": file_h, "propagate": False},
        # Application
        "core.exceptions": {"level": log_level, "handlers": file_h, "propagate": False},
        "core.db": {"level": log_level, "handlers": file_h, "propagate": False},
        "core.utils": {"level": log_level, "handlers": file_h, "propagate": False},
        # celery tasks
        "tasks.base": {"level": log_level, "handlers": file_h, "propagate": False},
        "tasks.debug": {"level": log_level, "handlers": file_h, "propagate": False},
    }


# ---------------------------------------------------------------------------
# Main config
# ---------------------------------------------------------------------------


def get_logging_config() -> Dict[str, Any]:
    """
    Returns a logging configuration dictionary compatible with logging.config.dictConfig().

    Process type and log level are read from settings, driven by environment variables
    (PROCESS_TYPE, LOG_LEVEL). Defaults to FASTAPI if PROCESS_TYPE is not set.
    """
    is_fastapi = settings.process_type == ProcessType.FASTAPI
    is_dev = settings.env in ["development", "testing"]
    log_level = settings.log_level.upper()
    filename = settings.log_directory / f"{settings.log_name}.log"

    file_h = ["file_watcher", "console"] if is_dev else ["file_watcher"]
    web_h = ["web_file_watcher", "web_console"] if is_dev else ["web_file_watcher"]

    if is_fastapi:
        loggers = _build_fastapi_loggers(log_level, file_h=file_h, web_h=web_h)
    else:
        loggers = _build_celery_loggers(log_level, file_h=file_h)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": _build_filters(is_fastapi),
        "formatters": _build_formatters(),
        "handlers": _build_handlers(filename, is_fastapi=is_fastapi, is_dev=is_dev),
        "loggers": loggers,
    }
