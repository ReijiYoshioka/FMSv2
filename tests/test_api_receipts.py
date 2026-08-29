import io

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
            "RECEIPT_DAILY_LIMIT": 3,
        }
    )
    with app.app_context():
        init_db(str(db_path))
    yield app


def _token(client):
    client.get("/monthly")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def _image_data(csrf_token, filename="receipt.jpg", content_type="image/jpeg", size=64):
    return {
        "image": (io.BytesIO(b"\xff\xd8\xff\xe0" + b"0" * size), filename, content_type),
        "csrf_token": csrf_token,
    }


def _stub_extract(monkeypatch, return_value=None, side_effect=None):
    def fake(api_key, model, image_bytes, mime_type, category_names):
        if side_effect:
            raise side_effect
        return return_value

    monkeypatch.setattr(gemini_client, "extract_receipt", fake)


def test_read_receipt_success(auth_client, monkeypatch):
    _stub_extract(
        monkeypatch,
        return_value={
            "date": "2026-08-20",
            "store_name": "スーパーやまだ",
            "items": [
                {"item_name": "牛乳", "amount": 200, "category_name": "食費"},
                {"item_name": "ノート", "amount": 150, "category_name": "存在しないカテゴリー"},
            ],
        },
    )
    resp = auth_client.post(
        "/api/receipts",
        data=_image_data(_token(auth_client)),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    result = resp.get_json()
    assert result["date"] == "2026-08-20"
    assert result["description"] == "スーパーやまだ"
    assert result["items"][0] == {"item_name": "牛乳", "amount": 200, "category_id": 1}
    assert result["items"][1]["category_id"] is None


def test_requires_login(client):
    resp = client.post(
        "/api/receipts",
        data=_image_data("dummy"),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_requires_csrf(auth_client, monkeypatch):
    _stub_extract(monkeypatch, return_value={"items": [{"item_name": "x", "amount": 1}]})
    resp = auth_client.post(
        "/api/receipts",
        data=_image_data("invalid-token"),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 403


def test_image_field_required(auth_client):
    resp = auth_client.post(
        "/api/receipts",
        data={"csrf_token": _token(auth_client)},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_rejects_non_image_mime(auth_client):
    resp = auth_client.post(
        "/api/receipts",
        data=_image_data(_token(auth_client), filename="receipt.txt", content_type="text/plain"),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "画像形式" in resp.get_json()["error"]


def test_rejects_oversized_image(auth_client):
    resp = auth_client.post(
        "/api/receipts",
        data=_image_data(_token(auth_client), size=9 * 1024 * 1024),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "8MB" in resp.get_json()["error"]


def test_missing_api_key_returns_error(auth_client):
    auth_client.application.config["GEMINI_API_KEY"] = ""
    resp = auth_client.post(
        "/api/receipts",
        data=_image_data(_token(auth_client)),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 502
    assert "利用できません" in resp.get_json()["error"]


def test_daily_limit_exceeded(auth_client, app):
    with app.app_context():
        db = get_db()
        for _ in range(3):
            db.execute("INSERT INTO receipt_read_attempts (user_id) VALUES (1)")
        db.commit()
    resp = auth_client.post(
        "/api/receipts",
        data=_image_data(_token(auth_client)),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 429


def test_upstream_failure_returns_502(auth_client, monkeypatch):
    _stub_extract(monkeypatch, side_effect=ExternalServiceError("読み取りに失敗しました。"))
    resp = auth_client.post(
        "/api/receipts",
        data=_image_data(_token(auth_client)),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 502


def test_no_items_extracted_returns_error(auth_client, monkeypatch):
    _stub_extract(monkeypatch, return_value={"items": []})
    resp = auth_client.post(
        "/api/receipts",
        data=_image_data(_token(auth_client)),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
