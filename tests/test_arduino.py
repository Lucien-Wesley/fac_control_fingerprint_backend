import pytest


def test_ports_requires_auth(client):
    # No token -> 401
    r = client.get("/arduino/ports")
    assert r.status_code == 401


def test_ports_with_user_ok(client, user_headers, monkeypatch):
    # Mock listing ports
    from utils import arduino

    def fake_list_ports():
        return [{"device": "COM3"}]

    def fake_status():
        return {"connected": False, "port": None, "baudrate": 9600}

    monkeypatch.setattr(arduino.arduino_manager, "list_ports", fake_list_ports)
    monkeypatch.setattr(arduino.arduino_manager, "status", fake_status)

    r = client.get("/arduino/ports", headers=user_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "ports" in data and isinstance(data["ports"], list)


def test_connect_requires_admin(client, user_headers, auth_headers, monkeypatch):
    from utils import arduino

    def fake_connect(port, baudrate=9600, timeout=2.0):
        return True, f"Connected to {port}"

    monkeypatch.setattr(arduino.arduino_manager, "connect", fake_connect)

    # Non-admin should be forbidden
    r = client.post("/arduino/connect", json={"port": "COM3"}, headers=user_headers)
    assert r.status_code == 403

    # Admin ok
    r = client.post("/arduino/connect", json={"port": "COM3"}, headers=auth_headers)
    assert r.status_code == 200


def test_disconnect_requires_admin(client, user_headers, auth_headers, monkeypatch):
    from utils import arduino

    def fake_disconnect():
        return True, "Disconnected"

    def fake_status():
        return {"connected": False, "port": None, "baudrate": 9600}

    monkeypatch.setattr(arduino.arduino_manager, "disconnect", fake_disconnect)
    monkeypatch.setattr(arduino.arduino_manager, "status", fake_status)

    r = client.post("/arduino/disconnect", headers=user_headers)
    assert r.status_code == 403

    r = client.post("/arduino/disconnect", headers=auth_headers)
    assert r.status_code == 200


def test_test_capture_admin_only(client, auth_headers, user_headers, monkeypatch):
    from utils import arduino

    def fake_capture(entity, entity_id, max_retries=3, per_try_timeout=8.0):
        return True, "OK"

    monkeypatch.setattr(arduino.arduino_manager, "capture_fingerprint", fake_capture)

    r = client.post(
        "/arduino/test-capture",
        json={"entity": "student", "entity_id": 1},
        headers=user_headers,
    )
    assert r.status_code == 403

    r = client.post(
        "/arduino/test-capture",
        json={"entity": "student", "entity_id": 1},
        headers=auth_headers,
    )
    assert r.status_code == 200
