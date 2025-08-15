import pytest

from app.auth.repositories import AuthRepository


@pytest.mark.auth
@pytest.mark.asyncio
async def test_insert_user(get_test_db):
    """Test user Insert"""
    repo = AuthRepository(get_test_db)
    await repo.insert_user("testuser", "test@example.com", "hashed_password")
    data: dict = await repo.get_user_by_username("testuser")
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    # We will return password_hash as its needed in UserService.authenticate_user
    assert data["password_hash"] == "hashed_password"


@pytest.mark.auth
@pytest.mark.asyncio
async def test_refresh_token_logic(get_test_db):
    """Test user Insert"""
    repo = AuthRepository(get_test_db)
    await repo.insert_user("testuser", "test@example.com", "hashed_password")
    data: dict = await repo.get_user_by_username("testuser")
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    await repo.insert_refresh_token("testuser", "token1")
    assert await repo.verify_refresh_token("testuser", "token1")
    await repo.insert_refresh_token("testuser", "token2")
    await repo.insert_refresh_token("testuser", "token3")
    assert await repo.verify_refresh_token("testuser", "token2")
    # confirming deletion of the initial token1
    assert False == await repo.verify_refresh_token("testuser", "token1")


@pytest.mark.auth
@pytest.mark.asyncio
async def test_logout_user(get_test_db):
    """Test user Insert"""
    repo = AuthRepository(get_test_db)
    await repo.insert_user("testuser", "test@example.com", "hashed_password")
    data: dict = await repo.get_user_by_username("testuser")
    assert data["username"] == "testuser"
    await repo.insert_refresh_token("testuser", "token1")
    assert await repo.verify_refresh_token("testuser", "token1")
    await repo.logout_user(1)
    assert False == await repo.verify_refresh_token("testuser", "token1")
