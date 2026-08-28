from fmsv2 import create_app


def test_session_cookie_secure_follows_force_https(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "test.db"),
            "SECRET_KEY": "test-secret-key",
            "FORCE_HTTPS": True,
        }
    )
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_session_cookie_not_secure_by_default(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "test.db"),
            "SECRET_KEY": "test-secret-key",
        }
    )
    assert app.config["SESSION_COOKIE_SECURE"] is False
