import pytest


@pytest.mark.auth
def test_register_user(client):
    """Test user registration"""
    user_data = {"email": "test@example.com", "username": "testuser", "password": "Testpassword123"}
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert "hashed_password" not in data  # Should not return password


@pytest.mark.auth
def test_login_user(client):
    """Test user login"""
    # First register a user
    register_data = {"email": "login@example.com", "username": "loginuser", "password": "Loginpassword123"}
    res = client.post("/auth/register", json=register_data)
    # Now try to login
    login_data = {"username": "loginuser", "password": "Loginpassword123"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = client.post("/auth/login", data=login_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
