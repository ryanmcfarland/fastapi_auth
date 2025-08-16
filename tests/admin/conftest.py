import pytest_asyncio

from app.core.utils import load_sql_query
from app.auth.models import RegisterRequest
from app.auth.service import UserService


@pytest_asyncio.fixture(scope="function")
async def add_user(reset_database, tests_directory, get_test_db):
    register = RegisterRequest(username="admin_user", email="testuser@dummy.com", password="DummyPass1")
    await UserService(get_test_db).register_user(register)
    query = load_sql_query("insert_admin", base_path=tests_directory)
    await get_test_db.execute(query)
    yield "admin_user", "DummyPass1"
