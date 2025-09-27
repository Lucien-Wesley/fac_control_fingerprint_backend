import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
import os
import importlib
import tempfile
from typing import Dict

import pytest
from utils.db import db


@pytest.fixture(scope="session")
def test_db_path() -> str:
    # Create a temp SQLite file for tests
    fd, path = tempfile.mkstemp(prefix="test_app_", suffix=".db")
    os.close(fd)
    return f"sqlite:///{path}"


@pytest.fixture(scope="session")
def test_app(test_db_path):
    # Ensure the app reads the test DB path on import
    os.environ["DATABASE_URL"] = test_db_path
    # Reload the app module so create_app() uses the env var
    import app as app_module
    importlib.reload(app_module)
    return app_module.app


@pytest.fixture()
def client(test_app):
    test_app.config.update({
        "TESTING": True,
    })
    with test_app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_db(test_app):
    # Ensure a clean schema and empty tables for each test
    with test_app.app_context():
        db.drop_all()
        db.create_all()


@pytest.fixture()
def auth_headers(client) -> Dict[str, str]:
    # Register admin if not exists, then login
    client.post("/auth/register", json={
        "username": "admin",
        "email": "admin@example.com",
        "password": "Admin123!",
        "role": "admin",
    })
    res = client.post("/auth/login", json={
        "identifier": "admin",
        "password": "Admin123!",
    })
    data = res.get_json() or {}
    token = data.get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_headers(client) -> Dict[str, str]:
    # Register normal user if not exists, then login
    client.post("/auth/register", json={
        "username": "user1",
        "email": "user1@example.com",
        "password": "User123!",
        "role": "user",
    })
    res = client.post("/auth/login", json={
        "identifier": "user1",
        "password": "User123!",
    })
    data = res.get_json() or {}
    token = data.get("access_token")
    return {"Authorization": f"Bearer {token}"}
