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
# Filters, formatters
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


# ---------------------------------------------------------------------------
# Handlers
# _build_handler_map() is dynamic — console handlers are only included in dev.
# _build_handlers() only needs filename; all handlers are always returned and
# unused ones are ignored by dictConfig.
# ---------------------------------------------------------------------------


def _build_handler_map(is_dev: bool) -> Dict[str, list[str]]:
    return {
        "file": ["file_watcher", "console"] if is_dev else ["file_watcher"],
        "web": ["web_file_watcher", "web_console"] if is_dev else ["web_file_watcher"],
        "task": ["task_file_watcher", "task_console"] if is_dev else ["task_file_watcher"],
    }


def _build_handlers(filename: Path, is_fastapi: bool) -> Dict[str, Any]:
    """
    All handler definitions live here.

    Only handlers relevant to the current process type and environment are selected into the returned dict.

    We don't return all handlers as celery workers would attempt to construct the web handlers (with correlation_id filter)
    and fail since asgi_correlation_id is not imported in that process. By conditionally including the web handlers only in FastAPI processes, we avoid this issue entirely.
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

    fastapi_handlers = {
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
    }

    handlers = {**all_handlers, **fastapi_handlers} if is_fastapi else {**all_handlers}
    return handlers


# ---------------------------------------------------------------------------
# Logger specs
# (logger_name -> (level | None, handler_key))
# None level means "inherit from log_level at build time"
# handler_key is resolved against handler_map in _resolve_loggers()
# ---------------------------------------------------------------------------

_FASTAPI_LOGGER_SPEC: Dict[str, tuple[str | None, str]] = {
    # Infrastructure
    "uvicorn": ("WARNING", "file"),
    "uvicorn.access": ("WARNING", "file"),
    "uvicorn.error": ("WARNING", "file"),
    "gunicorn": ("WARNING", "file"),
    "fastapi": ("WARNING", "file"),
    # FastAPI Backend App (infrastructure loggers without correlation_id)
    "core.utils": (None, "file"),
    "api.startup": ("INFO", "file"),
    # FastAPI Backend App (web handlers with correlation_id)
    "api.routing": (None, "web"),
    "api.middleware": (None, "web"),
    # FastAPI Routes & Services (web handlers with correlation_id)
    "core.exceptions": (None, "web"),
    "core.db": (None, "web"),
    "admin.routes": ("INFO", "web"),
    "models.validators": (None, "web"),
    "killteam.validators": (None, "web"),
}

_CELERY_LOGGER_SPEC: Dict[str, tuple[str | None, str]] = {
    # Infrastructure
    "celery": (None, "file"),
    "celery.beat": (None, "file"),
    "celery.app.trace": (None, "file"),
    "celery.worker": (None, "file"),
    "celery.worker.strategy": (None, "file"),
    "celery.worker.consumer": (None, "file"),
    # Application
    "core.exceptions": (None, "file"),
    "core.db": (None, "file"),
    "core.utils": (None, "file"),
    # Celery tasks (task formatter includes task name + id)
    "tasks.base": (None, "task"),
    "tasks.debug": (None, "task"),
}


def _resolve_loggers(
    spec: Dict[str, tuple[str | None, str]],
    log_level: str,
    handler_map: Dict[str, list[str]],
) -> Dict[str, Any]:
    return {
        name: {
            "level": level or log_level,
            "handlers": handler_map[handler_key],
            "propagate": False,
        }
        for name, (level, handler_key) in spec.items()
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

    spec = _FASTAPI_LOGGER_SPEC if is_fastapi else _CELERY_LOGGER_SPEC
    handler_map = _build_handler_map(is_dev)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": _build_filters(is_fastapi),
        "formatters": _build_formatters(),
        "handlers": _build_handlers(filename, is_fastapi),
        "loggers": _resolve_loggers(spec, log_level, handler_map),
    }
