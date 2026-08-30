import pytest

from fmsv2 import create_app
from fmsv2.db import get_db, init_db
from fmsv2.services import gemini_client
from fmsv2.services.errors import ExternalServiceError


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
            "GEMINI_API_KEY": "test-gemini-key",
            "PLACE_SUGGEST_DAILY_LIMIT": 3,
        }
    )
    with app.app_context():
        init_db(str(db_path))
    yield app


def _stub_suggest(monkeypatch, return_value=None, side_effect=None, capture=None):
    def fake(api_key, model, query, lat, lng):
        if capture is not None:
            capture.append({"query": query, "lat": lat, "lng": lng})
        if side_effect:
            raise side_effect
        return return_value if return_value is not None else []

    monkeypatch.setattr(gemini_client, "suggest_places", fake)


def test_suggest_success(auth_client, monkeypatch):
    _stub_suggest(monkeypatch, return_value=["スターバックス 東京駅店", "ドトールコーヒー"])
    resp = auth_client.get("/api/places/suggest?q=%E3%82%B9%E3%82%BF&lat=35.68&lng=139.76")
    assert resp.status_code == 200
    assert resp.get_json()["suggestions"] == ["スターバックス 東京駅店", "ドトールコーヒー"]


def test_requires_login(client):
    resp = client.get("/api/places/suggest?q=ab")
    assert resp.status_code == 401


def test_short_query_skips_gemini_call(auth_client, monkeypatch):
    calls = []
    _stub_suggest(monkeypatch, return_value=["dummy"], capture=calls)
    resp = auth_client.get("/api/places/suggest?q=a")
    assert resp.status_code == 200
    assert resp.get_json()["suggestions"] == []
    assert calls == []


def test_missing_api_key_returns_error(auth_client):
    auth_client.application.config["GEMINI_API_KEY"] = ""
    resp = auth_client.get("/api/places/suggest?q=ab")
    assert resp.status_code == 502
    assert "利用できません" in resp.get_json()["error"]


def test_daily_limit_exceeded(auth_client, app):
    with app.app_context():
        db = get_db()
        for _ in range(3):
            db.execute(
                "INSERT INTO api_call_attempts (user_id, endpoint) VALUES (1, 'place_suggest')"
            )
        db.commit()
    resp = auth_client.get("/api/places/suggest?q=ab")
    assert resp.status_code == 429


def test_invalid_coordinates_pass_none(auth_client, monkeypatch):
    calls = []
    _stub_suggest(monkeypatch, return_value=[], capture=calls)
    resp = auth_client.get("/api/places/suggest?q=ab&lat=not-a-number&lng=999")
    assert resp.status_code == 200
    assert calls == [{"query": "ab", "lat": None, "lng": None}]


def test_upstream_failure_returns_502(auth_client, monkeypatch):
    _stub_suggest(monkeypatch, side_effect=ExternalServiceError("候補の取得に失敗しました。"))
    resp = auth_client.get("/api/places/suggest?q=ab")
    assert resp.status_code == 502
