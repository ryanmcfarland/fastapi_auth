import pytest

from fastapi.testclient import TestClient

from fixtures.auth import UserContext


@pytest.mark.admin
def test_admin_pool_stats(client: TestClient, pytestadmin_user: UserContext):
    """Test user registration"""
    admin_ctx = pytestadmin_user
    login_data = {"username": admin_ctx.username, "password": admin_ctx.password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = client.post("/auth/login", data=login_data, headers=headers)
    assert response.status_code == 200
    token = response.json().get("access_token")
    headers = {"Authorization": f"bearer {token}"}
    stats = client.get("/admin/database/pool_stats", headers=headers)
    assert stats.status_code == 200
    assert set(stats.json().keys()) == set(["pool_stats", "pool_config"])


@pytest.mark.admin
def test_user_pool_stats(client: TestClient, pytestuser_user: UserContext):
    """Test user registration"""
    user_ctx = pytestuser_user
    login_data = {"username": user_ctx.username, "password": user_ctx.password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = client.post("/auth/login", data=login_data, headers=headers)
    assert response.status_code == 200
    token = response.json().get("access_token")
    headers = {"Authorization": f"bearer {token}"}
    stats = client.get("/admin/database/pool_stats", headers=headers)
    assert stats.status_code == 403
    assert stats.json() == {"detail": "You do not have permission to perform this action."}
