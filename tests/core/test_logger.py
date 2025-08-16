import pytest
import logging
import logging.config

from app.core.logging import get_logging_config


def test_get_logging_config_returns_dict():
    """Test that get_logging_config returns a dictionary."""
    config = get_logging_config()
    assert isinstance(config, dict)


def test_get_logging_config_has_required_keys():
    """Test that the config contains expected top-level keys."""
    config = get_logging_config()
    expected_keys = ["version", "formatters", "handlers", "loggers"]
    for key in expected_keys:
        assert key in config


def test_logger_initialization_with_config():
    """Test that a logger can be initialized with the config."""
    config = get_logging_config()
    # This should not raise an exception
    logging.config.dictConfig(config)
    # Get a logger and verify it works
    logger = logging.getLogger("core.utils")
    assert len(logger.handlers) > 0
