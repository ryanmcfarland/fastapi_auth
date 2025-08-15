import pytest

from fastapi import HTTPException

from app.auth.utils import TokenUtils
from app.auth.models import RegisterRequest, UserResponse
from app.auth.service import UserService


@pytest.mark.auth
@pytest.mark.asyncio
async def test_register_user(get_test_db):
    """Test user Insert"""
    service = UserService(get_test_db)
    register = RegisterRequest(username="testuser", email="testuser@dummy.com", password="DummyPass1")
    user_response = await service.register_user(register)
    assert isinstance(user_response, UserResponse)
    assert user_response.username == "testuser"
    assert user_response.user_roles == ["user"]


@pytest.mark.auth
@pytest.mark.asyncio
async def test_login_user_tokens(get_test_db):
    """Test user Insert"""
    service = UserService(get_test_db)
    register = RegisterRequest(username="testuser", email="testuser@dummy.com", password="DummyPass1")
    await service.register_user(register)
    tokens = await service.login_user("testuser", "DummyPass1")
    assert set(tokens.keys()) == set(["access_token", "refresh_token"])
    token_utils = TokenUtils()
    access_info = token_utils.decode_token(tokens.get("access_token"))
    assert access_info["type"] == "access"
    assert access_info["sub"] == "testuser"
    refresh_info = token_utils.decode_token(tokens.get("refresh_token"))
    assert refresh_info["type"] == "refresh"
    assert refresh_info["sub"] == "testuser"


@pytest.mark.auth
@pytest.mark.asyncio
async def test_authentic_user(get_test_db):
    """Test user Insert"""
    service = UserService(get_test_db)
    register = RegisterRequest(username="testuser", email="testuser@dummy.com", password="DummyPass1")
    await service.register_user(register)
    user: dict = await service.authenticate_user("testuser", "DummyPass1")
    assert user["username"] == "testuser"
    assert user["user_roles"] == ["user"]
    pw_user: dict = await service.authenticate_user("testuser", "DummyPassWrong")
    assert pw_user is None
    no_user: dict = await service.authenticate_user("WrongTestuser", "DummyPassWrong")
    assert no_user is None


@pytest.mark.auth
@pytest.mark.asyncio
async def test_logout_user(get_test_db):
    """Test user Insert"""
    service = UserService(get_test_db)
    register = RegisterRequest(username="testuser", email="testuser@dummy.com", password="DummyPass1")
    await service.register_user(register)
    tokens = await service.login_user("testuser", "DummyPass1")
    test_token = await service.verify_refresh_token(tokens["refresh_token"])
    assert isinstance(test_token, str)
    await service.logout_user(1)
    # test for the incoming HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await service.verify_refresh_token(tokens["refresh_token"])
    assert str(excinfo.value.detail) == "Invalid token"
