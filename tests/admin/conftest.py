from typing import AsyncGenerator, Tuple

import pytest_asyncio


from app.core.utils import load_sql_query
from app.auth.models import RegisterRequest
from app.auth.service import UserService


@pytest_asyncio.fixture(scope="function")
async def add_user(get_test_db) -> AsyncGenerator[Tuple[str, str], None]:
    register = RegisterRequest(username="admin_user", email="testuser@dummy.com", password="DummyPass1")
    await UserService(get_test_db).register_user(register)
    yield "admin_user", "DummyPass1"


@pytest_asyncio.fixture(scope="function")
async def add_admin_user(add_user, get_test_db, tests_directory) -> AsyncGenerator[Tuple[str, str], None]:
    query = load_sql_query("insert_admin", base_path=tests_directory)
    await get_test_db.execute(query)
    yield add_user
