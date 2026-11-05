import logging
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from admin_settings import AdminTestSettings
from migrationRunner import PostgreSQLMigrationRunner

from config import get_settings
from app.core.db import AsyncDatabase

log = logging.getLogger("conftest.database")

settings = get_settings()


@pytest.fixture(scope="session")
def database_directory() -> Path:
    """Returns the database directory path"""
    return settings.repo_directory


@pytest.fixture(scope="session")
def test_sql_directory(database_directory) -> Path:
    """Returns the test SQL directory path"""
    return database_directory / "tests" / "sql_queries"


### Database Fixtures ###


@pytest_asyncio.fixture(scope="session")
async def admin_db(admin_settings: AdminTestSettings) -> AsyncGenerator[AsyncDatabase, None]:
    log.warning("Creating admin_db fixture")
    db = AsyncDatabase(connection_string=admin_settings.superuser_database_url)
    await db.initialize()
    yield db
    await db.close()


@pytest_asyncio.fixture(scope="session")
async def test_db() -> AsyncGenerator[AsyncDatabase, None]:
    log.warning("Creating test_db fixture")
    db = AsyncDatabase(prepare_threshold=None)
    await db.initialize()
    result = await db.health_check()
    if not result:
        log.error("Database health check failed during test_db fixture setup")
        raise RuntimeError("Database health check failed during test_db fixture setup")
    yield db
    await db.close()


@pytest_asyncio.fixture(scope="function")
async def initialized_test_db(
    test_db: AsyncDatabase,
    admin_db: AsyncDatabase,
    database_directory: Path,
) -> AsyncGenerator[AsyncDatabase, None]:
    MigrationRunner = PostgreSQLMigrationRunner(database_directory, admin_db)
    log.warning("running: initialized_test_db")
    try:
        await MigrationRunner.run_all_down()
        await MigrationRunner.setup_database()
        yield test_db
    except Exception as e:
        log.error(f"initialized_test_db({e}) -> database will need checked.")
