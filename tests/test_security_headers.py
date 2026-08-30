import pytest

from fmsv2 import create_app
from fmsv2.db import init_db


@pytest.fixture
def https_app(tmp_path):
    db_path = tmp_path / "test.db"
    log_path = tmp_path / "logs" / "app_access_log.txt"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "SECRET_KEY": "test-secret-key",
            "ACCESS_LOG_PATH": str(log_path),
            "HEALTHCHECK_TOKEN": "test-healthcheck-token",
            "FORCE_HTTPS": True,
        }
    )
    with app.app_context():
        init_db(str(db_path))
    return app


def test_hsts_present_when_force_https_enabled(https_app):
    resp = https_app.test_client().get("/login")
    assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]


def test_security_headers_present(client):
    resp = client.get("/login")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "same-origin"
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]


def test_hsts_absent_when_force_https_disabled(client):
    resp = client.get("/login")
    assert "Strict-Transport-Security" not in resp.headers
