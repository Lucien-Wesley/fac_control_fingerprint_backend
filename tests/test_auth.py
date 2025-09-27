def test_register_and_login(client):
    # Register
    r = client.post("/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "Secret123!",
        "role": "user",
    })
    assert r.status_code in (201, 400)  # 400 if re-run

    # Login
    r = client.post("/auth/login", json={
        "identifier": "alice",
        "password": "Secret123!",
    })
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data
    assert data.get("user", {}).get("username") == "alice"


def test_admin_login(client):
    # Register an admin
    r = client.post("/auth/register", json={
        "username": "admin",
        "email": "admin@example.com",
        "password": "Admin123!",
        "role": "admin",
    })
    assert r.status_code in (201, 400)

    # Login as admin
    r = client.post("/auth/login", json={
        "identifier": "admin",
        "password": "Admin123!",
    })
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data
    assert data.get("user", {}).get("role") == "admin"
