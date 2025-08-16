import logging
import logging.config

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.globals import initialize_database, close_database
from app.core.logging import get_logging_config

log = logging.getLogger("core.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for API start-up functionality."""
    log.info("lifespan called - initialising application")
    config = get_logging_config()
    logging.config.dictConfig(config)
    await initialize_database()
    yield
    log.warning("lifespan ending - application terminating")
    await close_database()
