import pytest

from fastapi.exceptions import HTTPException


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


@pytest.mark.auth
def test_logout_and_refresh_request(client):
    """Test user login"""
    # First register a user
    register_data = {"email": "login@example.com", "username": "loginuser", "password": "Loginpassword123"}
    res = client.post("/auth/register", json=register_data)
    assert res.status_code == 201
    # Now try to login
    login_data = {"username": "loginuser", "password": "Loginpassword123"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    # login - this will set a cookie within the client AND also the response object
    response = client.post("/auth/login", data=login_data, headers=headers)
    assert response.status_code == 200
    assert response.cookies.get("refresh_token") == client.cookies.get("refresh_token")
    # TODO - updating cookies to remove secure in TESTING / DEV -> client doesn't use https
    client.cookies.set("refresh_token", client.cookies.get("refresh_token"))
    # refresh - verify that refresh_token (provided via cookie) creates an access_token
    verify_response = client.post("/auth/refresh")
    assert verify_response.status_code == 200
    assert "access_token" in verify_response.json().keys()
    # logout - "refresh_token" cookie will be deleted from cookies within endpoint
    response = client.post("/auth/logout")
    assert response.cookies.get("refresh_token") is None
    # client has not deleted cookie so retry /auth/refresh so below end_point will work
    verify_response = client.post("/auth/refresh")
    assert verify_response.status_code == 401
    assert verify_response.json().get("detail") == "Invalid token"
