from models import Student, Professor
from utils.db import db


def test_student_registration_biometric_success(client, auth_headers, monkeypatch):
    # Mock Arduino capture success
    from utils import arduino

    def fake_capture(entity, entity_id, max_retries=3, per_try_timeout=8.0):
        assert entity == "student"
        assert isinstance(entity_id, int)
        return True, "OK"

    monkeypatch.setattr(arduino.arduino_manager, "capture_fingerprint", fake_capture)

    r = client.post(
        "/students",
        json={"name": "Jane", "email": "jane@example.com", "major": "CS"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["fingerprint_verified"] is True

    # Verify in DB
    s = Student.query.filter_by(email="jane@example.com").first()
    assert s is not None
    assert s.fingerprint_verified is True


def test_student_registration_biometric_failure_rollback(client, auth_headers, monkeypatch):
    # Mock Arduino capture failure
    from utils import arduino

    def fake_capture(entity, entity_id, max_retries=3, per_try_timeout=8.0):
        return False, "FAIL"

    monkeypatch.setattr(arduino.arduino_manager, "capture_fingerprint", fake_capture)

    r = client.post(
        "/students",
        json={"name": "John", "email": "john@example.com", "major": "Math"},
        headers=auth_headers,
    )
    # 400 from service raising ValueError
    assert r.status_code == 400

    # Ensure nothing persisted
    s = Student.query.filter_by(email="john@example.com").first()
    assert s is None


def test_professor_registration_biometric_success(client, auth_headers, monkeypatch):
    from utils import arduino

    def fake_capture(entity, entity_id, max_retries=3, per_try_timeout=8.0):
        assert entity == "professor"
        return True, "OK"

    monkeypatch.setattr(arduino.arduino_manager, "capture_fingerprint", fake_capture)

    r = client.post(
        "/professors",
        json={"name": "Dr. Smith", "email": "smith@example.com", "department": "Math"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["fingerprint_verified"] is True

    p = Professor.query.filter_by(email="smith@example.com").first()
    assert p is not None
    assert p.fingerprint_verified is True


def test_professor_registration_biometric_failure_rollback(client, auth_headers, monkeypatch):
    from utils import arduino

    def fake_capture(entity, entity_id, max_retries=3, per_try_timeout=8.0):
        return False, "FAIL"

    monkeypatch.setattr(arduino.arduino_manager, "capture_fingerprint", fake_capture)

    r = client.post(
        "/professors",
        json={"name": "Dr. Fail", "email": "fail@example.com", "department": "CS"},
        headers=auth_headers,
    )
    assert r.status_code == 400

    p = Professor.query.filter_by(email="fail@example.com").first()
    assert p is None
