import logging.config
from app.core.logging import get_logging_config


# Configure logging before workers start
def on_starting(server):
    """Called just before the master process is initialized."""
    config = get_logging_config()
    logging.config.dictConfig(config)


def worker_process_init(worker):
    """Called just after a worker has been forked."""
    # Re-configure logging for each worker if needed
    config = get_logging_config()
    logging.config.dictConfig(config)


# Standard gunicorn settings
bind = "0.0.0.0:8000"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
