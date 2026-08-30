from conftest import get_csrf_token


def _token(client):
    client.get("/monthly")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def test_change_password_success(auth_client):
    resp = auth_client.post(
        "/api/account",
        json={
            "current_password": "password123",
            "new_password": "newpassword456",
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 200

    logout_token = _token(auth_client)
    auth_client.post("/logout", data={"csrf_token": logout_token})

    login_token = get_csrf_token(auth_client, "/login")
    login_resp = auth_client.post(
        "/login",
        data={"username": "taro", "password": "newpassword456", "csrf_token": login_token},
    )
    assert login_resp.status_code == 302


def test_change_password_wrong_current_returns_403(auth_client):
    resp = auth_client.post(
        "/api/account",
        json={
            "current_password": "wrong-password",
            "new_password": "newpassword456",
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 403


def test_change_password_too_short_rejected(auth_client):
    resp = auth_client.post(
        "/api/account",
        json={
            "current_password": "password123",
            "new_password": "short",
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 400


def test_change_password_same_as_current_rejected(auth_client):
    resp = auth_client.post(
        "/api/account",
        json={
            "current_password": "password123",
            "new_password": "password123",
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 400


def test_account_requires_login(client):
    resp = client.post("/api/account", json={"current_password": "a", "new_password": "b"})
    assert resp.status_code == 401


def test_change_password_requires_csrf(auth_client):
    resp = auth_client.post(
        "/api/account",
        json={
            "current_password": "password123",
            "new_password": "newpassword456",
            "csrf_token": "invalid-token",
        },
    )
    assert resp.status_code == 403


def test_change_password_exactly_min_length_accepted(auth_client):
    resp = auth_client.post(
        "/api/account",
        json={
            "current_password": "password123",
            "new_password": "12345678",
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 200


def test_change_password_missing_fields_rejected(auth_client):
    resp = auth_client.post("/api/account", json={"csrf_token": _token(auth_client)})
    assert resp.status_code == 400
