import pytest

from fastapi.testclient import TestClient

from app.auth.models import User

from tests.fixtures.auth import UserContext


@pytest.mark.auth
class TestRegisterRoutes:
    def test_register_user(self, client: TestClient):
        """Test user registration"""
        user_data = {"email": "test@example.com", "username": "testuser", "password": "Testpassword123"}
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 201

        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "hashed_password" not in data

    def test_register_fail_password(self, client: TestClient):
        """Test registration fails when password has no uppercase"""
        user_data = {"email": "test@example.com", "username": "testuser", "password": "testpassword123"}
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 422

        data = response.json()
        assert "errors" in data
        assert data["errors"]["password"] == "Value error, Password must contain at least one uppercase letter"


@pytest.mark.auth
class TestLoginRoutes:
    def test_login_user(self, client: TestClient):
        """Test user login"""
        register_data = {"email": "login@example.com", "username": "loginuser", "password": "Loginpassword123"}
        client.post("/auth/register", json=register_data)

        login_data = {"username": "loginuser", "password": "Loginpassword123"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post("/auth/login", data=login_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["refresh_expires_in"] > 0

        # Both tokens are exposed to the browser as HttpOnly cookies so the
        # frontend never has to read them from the response body. The refresh
        # token must never be readable from the JSON body.
        assert "refresh_token" not in data
        assert response.cookies.get("access_token") == data["access_token"]
        assert response.cookies.get("refresh_token") is not None

        # Next.js middleware and Server Components only see cookies with Path=/.
        set_cookie_headers = response.headers.get_list("set-cookie")
        assert any(header.startswith("access_token=") and "Path=/" in header for header in set_cookie_headers)
        assert any(header.startswith("refresh_token=") and "Path=/" in header for header in set_cookie_headers)

    def test_logout_and_refresh_request(self, client: TestClient):
        """Test logout and refresh flow"""
        register_data = {"email": "login@example.com", "username": "loginuser", "password": "Loginpassword123"}
        res = client.post("/auth/register", json=register_data)
        assert res.status_code == 201

        login_data = {"username": "loginuser", "password": "Loginpassword123"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post("/auth/login", data=login_data, headers=headers)
        assert response.status_code == 200
        assert response.cookies.get("access_token") == client.cookies.get("access_token")
        assert response.cookies.get("refresh_token") == client.cookies.get("refresh_token")

        verify_response = client.post("/auth/refresh")
        assert verify_response.status_code == 200
        refreshed = verify_response.json()
        assert "access_token" in refreshed
        assert refreshed["expires_in"] > 0
        assert refreshed["refresh_expires_in"] > 0

        # Refresh rewrites the access token cookie but reuses the refresh token.
        assert verify_response.cookies.get("access_token") == refreshed["access_token"]
        assert verify_response.cookies.get("access_token") == client.cookies.get("access_token")
        assert verify_response.cookies.get("refresh_token") is None

        response = client.post("/auth/logout")
        assert response.cookies.get("access_token") is None
        assert response.cookies.get("refresh_token") is None
        assert client.cookies.get("access_token") is None
        assert client.cookies.get("refresh_token") is None

        verify_response = client.post("/auth/refresh")
        assert verify_response.status_code == 401
        assert verify_response.json().get("detail") == "Authentication token missing"


@pytest.mark.auth
class TestProfileRoutes:
    def test_get_me_authenticated_user(
        self,
        authenticated_client: TestClient,
        pytestuser_user: UserContext,
    ):
        """Test /auth/me returns the current user when authenticated"""
        response = authenticated_client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == pytestuser_user.email
        assert data["username"] == pytestuser_user.username
        assert data["id"] == pytestuser_user.id

    def test_get_me_unauthenticated_user(self, client: TestClient):
        """Test /auth/me returns null for unauthenticated users"""
        response = client.get("/auth/me")

        assert response.status_code == 200
        assert response.json() is None

    def test_get_profile_authenticated_user(
        self,
        authenticated_client: TestClient,
        pytestuser_user: UserContext,
    ):
        """Test /auth/profile returns the logged in user's profile"""
        response = authenticated_client.get("/auth/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == pytestuser_user.email
        assert data["username"] == pytestuser_user.username
        assert data["id"] == pytestuser_user.id

    def test_get_profile_unauthenticated_user(self, client: TestClient):
        """Test /auth/profile rejects unauthenticated requests"""
        response = client.get("/auth/profile")

        assert response.status_code == 401
        assert response.json().get("detail") == "Not authenticated"
