"""
Test configuration and fixtures.

Fixtures are organized in tests/fixtures/:
 - database.py     Database and migration fixtures
 - auth.py         User authentication and registration fixtures
 - clients.py      HTTP client fixtures for testing endpoints
 - utilities.py    General utility fixtures

Note: Requires asyncio_default_fixture_loop_scope = "session" for database fixtures.
"""

import pytest

import logging.config

from app.core.logging import get_logging_config

pytest_plugins = [
    "fixtures.database",
    "fixtures.auth",
    "fixtures.clients",
    "fixtures.utilities",
]


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    config = get_logging_config()
    # logging.config.dictConfig(config)
