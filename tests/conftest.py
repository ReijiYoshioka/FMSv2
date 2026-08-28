import re

import pytest

from fmsv2 import create_app
from fmsv2.db import get_db, init_db
from fmsv2.services import users_repo

CSRF_INPUT_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    log_path = tmp_path / "logs" / "app_access_log.txt"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "SECRET_KEY": "test-secret-key",
            "ACCESS_LOG_PATH": str(log_path),
            "HEALTHCHECK_TOKEN": "test-healthcheck-token",
        }
    )
    with app.app_context():
        init_db(str(db_path))
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def get_csrf_token(client, path="/login"):
    resp = client.get(path)
    match = CSRF_INPUT_RE.search(resp.get_data(as_text=True))
    assert match, f"{path} にCSRFトークンが見つからない"
    return match.group(1)


@pytest.fixture
def create_test_user(app):
    def _create(username="taro", password="password123"):
        with app.app_context():
            users_repo.create_user(get_db(), username, password)

    return _create


@pytest.fixture
def auth_client(client, app, create_test_user):
    username = "taro"
    password = "password123"
    create_test_user(username, password)
    token = get_csrf_token(client, "/login")
    resp = client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token},
    )
    assert resp.status_code == 302
    return client
