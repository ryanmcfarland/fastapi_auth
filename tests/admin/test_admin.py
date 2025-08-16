import pytest


@pytest.mark.admin
def test_admin_pool_stats(client, add_admin_user):
    """Test user registration"""
    username, password = add_admin_user
    login_data = {"username": username, "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = client.post("/auth/login", data=login_data, headers=headers)
    assert response.status_code == 200
    token = response.json().get("access_token")
    headers = {"Authorization": f"bearer {token}"}
    stats = client.get("/admin/database/pool_stats", headers=headers)
    assert stats.status_code == 200
    assert set(stats.json().keys()) == set(["pool_stats", "pool_config"])


@pytest.mark.admin
def test_user_pool_stats(client, add_user):
    """Test user registration"""
    username, password = add_user
    login_data = {"username": username, "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = client.post("/auth/login", data=login_data, headers=headers)
    assert response.status_code == 200
    token = response.json().get("access_token")
    headers = {"Authorization": f"bearer {token}"}
    stats = client.get("/admin/database/pool_stats", headers=headers)
    assert stats.status_code == 401
    assert stats.json() == {"detail": "User [admin_user] Missing required role"}
