import pytest
import pytest_asyncio

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from main import app
from config import get_settings
from app.core.db import AsyncDatabase
from app.core.dependancies import get_db
from app.core.utils import load_sql_query

settings = get_settings()


"""
Note -> this requires the same event_loop (asyncio_default_fixture_loop_scope = "session")
If the database was greated on a per module basis and passed around, we could set the default to "module"
"""


@pytest_asyncio.fixture(scope="session", autouse=True)
async def get_test_db():
    test_db = AsyncDatabase()
    await test_db.initialize()
    yield test_db
    await test_db.close()


@pytest.fixture(scope="session", autouse=True)
def tests_directory():
    """Returns the current working directory as a Path object"""
    return settings.REPO_DIR / "tests"


@pytest_asyncio.fixture(scope="function", autouse=True)
async def reset_database(tests_directory, get_test_db):
    query = load_sql_query("setup_db", base_path=tests_directory)
    try:
        await get_test_db.execute(query)
        print(f"Query executed successfully")
    except Exception as e:
        print("here")


@pytest.fixture(scope="function")
def client(get_test_db):
    app.dependency_overrides[get_db] = lambda: get_test_db
    return TestClient(app)


@pytest.fixture(scope="function")
def pass_utc_now():
    return datetime.now(timezone.utc)


@pytest.fixture(scope="function")
def pass_parameters(pass_utc_now):
    utc_now = pass_utc_now
    yield utc_now


@pytest.fixture(scope="session")
def create_base_dir(tmp_path_factory):
    tmp_path_factory._given_basetemp = "root_dir_here"
    directory = tmp_path_factory.getbasetmp()
    return directory


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_files(tmp_path_factory, request):
    yield
    if request.session.testsfailed == 0:
        # shutil.rmtree(tmp_path_factory.getbasetmp())
        pass
