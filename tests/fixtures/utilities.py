"""
autouse fixtures
-----------------

Fixture Orders and Teardown:
  - For autouse fixtures with the same scope and no dependencies, pytest runs them in the order they are defined in the file. So if you have two autouse fixtures, A and B, defined in that order, pytest will run A first, then B.
  - During teardown (after the test function finishes), pytest reverses the order of execution. So B will tear down first, then A.

In our case:
    Setup:    cleanup_temp_files → manage_pytest_log
    Teardown: manage_pytest_log  → cleanup_temp_files
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from config import get_settings

from admin_settings import AdminTestSettings

settings = get_settings()


@pytest.fixture(scope="session")
def admin_settings() -> AdminTestSettings:
    return AdminTestSettings()


@pytest.fixture(scope="session", autouse=True)
def tests_directory() -> Path:
    """Returns the tests directory as a Path object"""
    return settings.repo_directory / "tests"


@pytest.fixture(scope="function")
def pass_utc_now():
    """Return current UTC datetime"""
    return datetime.now(timezone.utc)


@pytest.fixture(scope="function")
def pass_parameters(pass_utc_now):
    """Yield UTC datetime (alias for pass_utc_now)"""
    utc_now = pass_utc_now
    yield utc_now


@pytest.fixture(scope="session")
def create_base_dir(tmp_path_factory):
    """Create temporary base directory for tests"""
    tmp_path_factory._given_basetemp = "root_dir_here"
    directory = tmp_path_factory.getbasetmp()
    return directory


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_files(tmp_path_factory, request):
    """Cleanup temporary files after tests if all passed"""
    yield
    if request.session.testsfailed == 0:
        # shutil.rmtree(tmp_path_factory.getbasetmp())
        pass
