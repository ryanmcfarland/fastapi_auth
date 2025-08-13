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
