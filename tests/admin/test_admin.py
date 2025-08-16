import pytest


@pytest.mark.admin
def test_check_database(client, admin_user):
    """Test user registration"""
    username, password = admin_user
    login_data = {"username": username, "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = client.post("/auth/login", data=login_data, headers=headers)
    assert response.status_code == 200
    token = response.json().get("access_token")
    headers = {"Authorization": f"bearer {token}"}
    stats = client.get("/admin/database/pool_stats", headers=headers)
    assert stats.status_code == 200
    assert set(stats.json().keys()) == set(["pool_stats", "pool_config"])
