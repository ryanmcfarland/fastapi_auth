""" """

from typing import Dict, Any

from config import get_settings

settings = get_settings()


def get_optional_loggers() -> dict:
    return {
        # Psycopg loggers
        "psycopg": {"level": "DEBUG", "handlers": ["console", "file_watcher"], "propagate": False},
        "psycopg.connections": {"level": "DEBUG", "handlers": ["console", "file_watcher"], "propagate": False},
    }


def get_base_loggers(log_level: str = "INFO") -> dict:
    return {
        # FastAPI/Uvicorn loggers
        "uvicorn": {"level": "WARNING", "handlers": ["file_watcher"], "propagate": False},
        "uvicorn.access": {"level": "WARNING", "handlers": ["file_watcher"], "propagate": False},
        "uvicorn.error": {"level": "WARNING", "handlers": ["file_watcher"], "propagate": False},
        "gunicorn": {"level": "WARNING", "handlers": ["console", "file_watcher"], "propagate": False},
        "fastapi": {"level": "WARNING", "handlers": ["console", "file_watcher"], "propagate": False},
        # Core Application Loggers
        "admin.routes": {"level": "INFO", "handlers": ["web_console", "web_file_watcher"], "propagate": False},
        "core.startup": {"level": "INFO", "handlers": ["console", "file_watcher"], "propagate": False},
        # Application loggers
        "core.utils": {"level": log_level, "handlers": ["web_console", "web_file_watcher"], "propagate": False},
        "core.db": {"level": log_level, "handlers": ["web_console", "web_file_watcher"], "propagate": False},
    }


def get_logging_config() -> Dict[str, Any]:
    """
    Returns a logging configuration dictionary compatible with logging.config.dictConfig()

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    default_fmt = "%(levelname)s [%(asctime)s.%(msecs)03d] [pid:%(process)s] %(name)s : %(message)s"
    web_req_fmt = "%(levelname)s [%(asctime)s.%(msecs)03d] [pid:%(process)s] [ReqId:%(correlation_id)s] %(name)s : %(message)s"
    filename = f"{settings.LOG_DIRECTORY}/test.log"
    log_level: str = settings.LOG_LEVEL
    # set default logger dictionary
    loggers = get_base_loggers(log_level)
    if settings.LOG_INCLUDE_OPTIONAL:
        loggers.update(get_optional_loggers())

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "correlation_id": {
                "()": "asgi_correlation_id.CorrelationIdFilter",
                "uuid_length": 8,
                "default_value": "-",
            },
        },
        "formatters": {
            "default": {"format": default_fmt, "datefmt": "%Y-%m-%d %H:%M:%S"},
            "requests": {"format": web_req_fmt, "datefmt": "%Y-%m-%d %H:%M:%S"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "web_console": {
                "class": "logging.StreamHandler",
                "formatter": "requests",
                "filters": ["correlation_id"],
                "stream": "ext://sys.stdout",
            },
            "file_watcher": {
                "class": "logging.handlers.WatchedFileHandler",
                "formatter": "default",
                "filename": filename,
                "encoding": "utf8",
            },
            "web_file_watcher": {
                "class": "logging.handlers.WatchedFileHandler",
                "formatter": "requests",
                "filename": filename,
                "filters": ["correlation_id"],
                "encoding": "utf8",
                "mode": "a",
            },
        },
        "root": {"level": "ERROR", "handlers": ["console", "file_watcher"]},
        "loggers": loggers,
    }

    return config
