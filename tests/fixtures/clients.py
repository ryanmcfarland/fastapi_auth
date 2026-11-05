from typing import Callable, Generator

import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.db import AsyncDatabase
from app.core.dependancies import get_db

from fixtures.auth import UserContext

# ===========================================
# Client Factory Fixtures
# ===========================================


@pytest.fixture(scope="function")
def make_client(initialized_test_db) -> Callable[[], TestClient]:
    """Factory fixture to create authenticated clients for different users"""

    def _make_client() -> TestClient:
        app.dependency_overrides[get_db] = lambda: initialized_test_db
        client = TestClient(app)
        return client

    return _make_client


@pytest.fixture(scope="function")
def make_authenticated_client(make_client) -> Callable[[str, str], TestClient]:
    """Factory fixture to create authenticated clients for different users"""

    def _make_client(username: str, password: str) -> TestClient:
        client: TestClient = make_client()
        response = client.post("/auth/login", data={"username": username, "password": password}, headers={"Content-Type": "application/x-www-form-urlencoded"})
        token = response.json().get("access_token")
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client

    return _make_client


# ===========================================
# Client Fixtures
# ===========================================


@pytest.fixture(scope="function")
def client(initialized_test_db: AsyncDatabase) -> TestClient:
    """
    Create a test client with test database dependency overridden.
    TestClient does trigger the lifespan by default, so we can just override the get_db dependency to use our test_db and return the client.

    @pytest.fixture(scope="function")
    def client(test_db):
        app.dependency_overrides[get_db] = lambda: test_db
        with TestClient(app) as c:
            yield c
    """
    app.dependency_overrides[get_db] = lambda: initialized_test_db
    return TestClient(app)


@pytest.fixture(scope="function")
def authenticated_client(
    make_authenticated_client: Callable[[str, str], TestClient],
    pytestuser_user: UserContext,
) -> Generator[TestClient, None, None]:
    """Create an authenticated client for a regular test user"""
    user_ctx = pytestuser_user
    yield make_authenticated_client(user_ctx.username, user_ctx.password)
