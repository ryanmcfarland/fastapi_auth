import pytest
import asyncio

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from main import app  # type: ignore
from app.core.db import AsyncDatabase  # type: ignore
from app.core.dependancies import get_db  # type: ignore


test_db = AsyncDatabase()


def get_test_db() -> AsyncDatabase:
    return test_db


@pytest.fixture(scope="session")
def get_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_databases(get_event_loop):
    loop = get_event_loop
    loop.run_until_complete(get_test_db().initialize())
    yield
    loop.run_until_complete(get_test_db().close())


@pytest.fixture(scope="function", autouse=True)
def reset_database(get_event_loop):
    loop = get_event_loop
    loop.run_until_complete(get_test_db().execute("setup_db"))


@pytest.fixture(scope="function")
def client():
    app.dependency_overrides[get_db] = get_test_db
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
