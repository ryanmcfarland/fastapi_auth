import logging

from dataclasses import dataclass
from typing import Awaitable, Callable

import pytest
import pytest_asyncio

from app.core.utils import load_sql_query
from app.core.db import AsyncDatabase
from app.auth.models import RegisterUser, User

log = logging.getLogger("fixtures.auth")

from admin_settings import AdminTestSettings

# ===========================================
# Auth Test Models (internal)
# ===========================================


class PytestRegisterModel(RegisterUser):
    username: str = "pytestuser"
    email: str = "pytestuser@system.internal.pytest"
    password: str = "TestPass11"


# ===========================================
# Auth Test Context
# ===========================================


@dataclass
class UserContext:
    user: User
    username: str
    password: str

    @property
    def email(self) -> str:
        return self.user.email

    @property
    def id(self) -> int:
        return self.user.id


# ===========================================
# Auth Test Factory Fixtures
# ===========================================


@pytest.fixture(scope="function")
def pytestuser_user_factory(initialized_test_db: AsyncDatabase) -> Callable[..., Awaitable[UserContext]]:
    # load here to prevent a circular import (lazy import)
    from app.auth.service import AuthenticationService

    async def _factory(**overrides) -> UserContext:
        service = AuthenticationService(initialized_test_db)
        model = PytestRegisterModel(**overrides)
        await service.register_user(model)
        tokens = await service.login_user(model.username, model.password)
        user = await service.get_current_user(tokens.access_token)
        return UserContext(user=user, username=model.username, password=model.password)

    return _factory


@pytest.fixture(scope="function")
def user_info_factory() -> Callable:
    """Fixture factory to get user info for killteam tests"""

    from app.auth.service import AuthenticationService

    async def _get_user_info(database: AsyncDatabase, username: str, password: str = "TestPass11") -> UserContext:
        service = AuthenticationService(database)
        await service.reset_password(username, password)
        tokens = await service.login_user(username, password)
        user = await service.get_current_user(tokens.access_token)
        return UserContext(user=user, username=username, password=password)

    return _get_user_info


# ===========================================
# Auth Fixtures
# ===========================================


@pytest.fixture(scope="function")
def user_email_reset(admin_settings: AdminTestSettings) -> str:
    return admin_settings.user_email_reset


@pytest_asyncio.fixture(scope="function")
async def pytestuser_user(pytestuser_user_factory) -> UserContext:
    """Defaults to: pytestuser / TestPass11"""
    user_ctx = await pytestuser_user_factory()
    return user_ctx


@pytest_asyncio.fixture(scope="function")
async def pytestemail_user(pytestuser_user_factory: Callable, user_email_reset: str) -> UserContext:
    """Defaults to: pytestuser / TestPass11"""
    overrides = {"username": "pytestemailuser", "email": user_email_reset}
    user_ctx = await pytestuser_user_factory(**overrides)
    return user_ctx


@pytest_asyncio.fixture(scope="function")
async def pytestadmin_user(initialized_test_db: AsyncDatabase, test_sql_directory: str, pytestuser_user_factory: Callable) -> UserContext:
    """Defaults to: pytestuser / TestPass11"""
    overrides = {"username": "pytestadminuser", "email": "pytestadminuser@system.internal.pytest"}
    user_ctx: UserContext = await pytestuser_user_factory(**overrides)
    query = load_sql_query("insert_admin", base_path=test_sql_directory, query_dir=None)
    await initialized_test_db.execute(query, {"user_id": user_ctx.user.id})
    user_ctx.user.user_roles.append("admin")
    return user_ctx
