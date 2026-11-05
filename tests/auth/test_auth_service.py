import pytest

from app.core.db import AsyncDatabase

from app.auth.utils import TokenUtils
from app.auth.models import RegisterUser, ResponseUser, User
from app.auth.service import AuthenticationService, LoginTokens, RefreshedTokens
from app.auth.exceptions import InvalidTokenError


@pytest.fixture(scope="function")
def initialised_authentication_service(initialized_test_db: AsyncDatabase) -> AuthenticationService:
    return AuthenticationService(initialized_test_db)


@pytest.fixture(scope="function")
def registered_user_model() -> RegisterUser:
    return RegisterUser(username="testuser", email="testuser@dummy.com", password="DummyPass1")


@pytest.mark.auth
@pytest.mark.asyncio
async def test_register_user(
    initialised_authentication_service: AuthenticationService,
    registered_user_model: RegisterUser,
):
    """Test user Insert"""
    user_response = await initialised_authentication_service.register_user(registered_user_model)
    assert isinstance(user_response, ResponseUser)
    assert user_response.username == "testuser"
    assert user_response.user_roles == ["user"]


@pytest.mark.auth
@pytest.mark.asyncio
async def test_login_user_tokens(
    initialised_authentication_service: AuthenticationService,
    registered_user_model: RegisterUser,
):
    """Test user Insert"""
    await initialised_authentication_service.register_user(registered_user_model)
    tokens = await initialised_authentication_service.login_user("testuser", "DummyPass1")
    assert isinstance(tokens, LoginTokens)
    assert tokens.access_token
    assert tokens.refresh_token is not None
    token_utils = TokenUtils()
    access_info = token_utils.decode_token(tokens.access_token)
    assert access_info["type"] == "access"
    assert access_info["sub"] == "testuser"
    refresh_info = token_utils.decode_token(tokens.refresh_token)
    assert refresh_info["type"] == "refresh"
    assert refresh_info["sub"] == "testuser"


@pytest.mark.auth
@pytest.mark.asyncio
async def test_refresh_access_token(
    initialised_authentication_service: AuthenticationService,
    registered_user_model: RegisterUser,
):
    """Refreshing reuses the refresh token and only issues a new access token."""
    await initialised_authentication_service.register_user(registered_user_model)
    tokens = await initialised_authentication_service.login_user("testuser", "DummyPass1")

    refreshed = await initialised_authentication_service.refresh_access_token(tokens.refresh_token)

    assert isinstance(refreshed, RefreshedTokens)
    assert refreshed.access_token
    assert refreshed.expires_in > 0
    assert refreshed.refresh_expires_in > 0

    access_info = TokenUtils().decode_token(refreshed.access_token)
    assert access_info["type"] == "access"
    assert access_info["sub"] == "testuser"


@pytest.mark.auth
@pytest.mark.asyncio
async def test_authentic_user(
    initialised_authentication_service: AuthenticationService,
    registered_user_model: RegisterUser,
):
    """Test user Insert"""
    await initialised_authentication_service.register_user(registered_user_model)
    user_name = await initialised_authentication_service.authenticate_user("testuser", "DummyPass1")
    assert isinstance(user_name, User)
    assert user_name.username == "testuser"
    assert user_name.user_roles == ["user"]
    user_email = await initialised_authentication_service.authenticate_user("testuser@dummy.com", "DummyPass1")
    assert isinstance(user_email, User)
    assert user_email.username == "testuser"
    assert user_email.user_roles == ["user"]
    pw_user = await initialised_authentication_service.authenticate_user("testuser", "DummyPassWrong")
    assert pw_user is None
    no_user = await initialised_authentication_service.authenticate_user("WrongTestuser", "DummyPassWrong")
    assert no_user is None


@pytest.mark.auth
@pytest.mark.asyncio
async def test_logout_user(
    initialised_authentication_service: AuthenticationService,
    registered_user_model: RegisterUser,
):
    """Test user Insert"""
    await initialised_authentication_service.register_user(registered_user_model)
    tokens = await initialised_authentication_service.login_user("testuser", "DummyPass1")
    test_token = await initialised_authentication_service.verify_refresh_token(tokens.refresh_token)
    assert isinstance(test_token, str)
    # below endpoint requires a refresh_token to determine the username
    await initialised_authentication_service.logout_user(tokens.refresh_token)
    with pytest.raises(InvalidTokenError) as excinfo:
        await initialised_authentication_service.verify_refresh_token(tokens.refresh_token)
    assert str(excinfo.value.detail) == "Invalid or expired token"
