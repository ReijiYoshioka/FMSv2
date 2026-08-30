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
            "CHAT_DAILY_LIMIT": 3,
        }
    )
    with app.app_context():
        init_db(str(db_path))
    yield app


def _token(client):
    client.get("/monthly")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def _post(client, messages, csrf_token=None):
    return client.post(
        "/api/chat/parse",
        json={"csrf_token": csrf_token or _token(client), "messages": messages},
    )


def _stub_parse(monkeypatch, return_value=None, side_effect=None):
    def fake(api_key, model, messages, category_names, payment_method_names, today):
        if side_effect:
            raise side_effect
        return return_value

    monkeypatch.setattr(gemini_client, "parse_transaction_chat", fake)


def test_parse_complete(auth_client, monkeypatch):
    _stub_parse(
        monkeypatch,
        return_value={
            "status": "complete",
            "date": "2026-08-30",
            "description": "ランチ",
            "amount": 1200,
            "type": "expense",
            "category_name": "食費",
            "payment_method_name": "現金",
        },
    )
    resp = _post(auth_client, [{"role": "user", "text": "今日ランチ1200円"}])
    assert resp.status_code == 200
    result = resp.get_json()
    assert result["status"] == "complete"
    assert result["amount"] == 1200
    assert result["category_id"] == 1
    assert result["payment_method_id"] == 1


def test_parse_need_more_info(auth_client, monkeypatch):
    _stub_parse(
        monkeypatch, return_value={"status": "need_more_info", "question": "いくらですか？"}
    )
    resp = _post(auth_client, [{"role": "user", "text": "コンビニで買い物した"}])
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "need_more_info", "question": "いくらですか？"}


def test_requires_login(client):
    resp = client.post("/api/chat/parse", json={"messages": [{"role": "user", "text": "x"}]})
    assert resp.status_code == 401


def test_requires_csrf(auth_client, monkeypatch):
    _stub_parse(monkeypatch, return_value={"status": "need_more_info", "question": "?"})
    resp = _post(auth_client, [{"role": "user", "text": "x"}], csrf_token="invalid")
    assert resp.status_code == 403


def test_empty_messages_rejected(auth_client):
    resp = _post(auth_client, [])
    assert resp.status_code == 400


def test_malformed_message_rejected(auth_client):
    resp = _post(auth_client, [{"role": "bot", "text": "x"}])
    assert resp.status_code == 400


def test_too_many_turns_rejected(auth_client):
    messages = [{"role": "user", "text": f"turn {i}"} for i in range(20)]
    resp = _post(auth_client, messages)
    assert resp.status_code == 400


def test_missing_api_key_returns_error(auth_client):
    auth_client.application.config["GEMINI_API_KEY"] = ""
    resp = _post(auth_client, [{"role": "user", "text": "今日ランチ1200円"}])
    assert resp.status_code == 502


def test_daily_limit_exceeded(auth_client, app):
    with app.app_context():
        db = get_db()
        for _ in range(3):
            db.execute("INSERT INTO api_call_attempts (user_id, endpoint) VALUES (1, 'chat')")
        db.commit()
    resp = _post(auth_client, [{"role": "user", "text": "今日ランチ1200円"}])
    assert resp.status_code == 429


def test_upstream_failure_returns_502(auth_client, monkeypatch):
    _stub_parse(monkeypatch, side_effect=ExternalServiceError("解析に失敗しました。"))
    resp = _post(auth_client, [{"role": "user", "text": "今日ランチ1200円"}])
    assert resp.status_code == 502
