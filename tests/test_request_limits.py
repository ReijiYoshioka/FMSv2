import io

import pytest

from fmsv2 import create_app
from fmsv2.db import init_db


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
            "MAX_CONTENT_LENGTH": 1024,
        }
    )
    with app.app_context():
        init_db(str(db_path))
    yield app


def _token(client):
    client.get("/monthly")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def test_oversized_upload_returns_413_json(auth_client):
    data = {
        "file": (io.BytesIO(b"0" * 2048), "big.csv"),
        "csrf_token": _token(auth_client),
    }
    resp = auth_client.post("/api/csv", data=data, content_type="multipart/form-data")
    assert resp.status_code == 413
    assert "error" in resp.get_json()
