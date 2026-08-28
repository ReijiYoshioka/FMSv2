from conftest import get_csrf_token


def test_register_success(client):
    token = get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={"username": "hanako", "password": "password123", "csrf_token": token},
    )
    assert resp.status_code == 200
    assert "登録が完了しました" in resp.get_data(as_text=True)


def test_register_username_too_short(client):
    token = get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={"username": "ab", "password": "password123", "csrf_token": token},
    )
    assert "3文字以上" in resp.get_data(as_text=True)


def test_register_password_too_short(client):
    token = get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={"username": "hanako", "password": "short", "csrf_token": token},
    )
    assert "8文字以上" in resp.get_data(as_text=True)


def test_register_duplicate_username(client, create_test_user):
    create_test_user("taro", "password123")
    token = get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={"username": "taro", "password": "password123", "csrf_token": token},
    )
    assert "既に使われています" in resp.get_data(as_text=True)


def test_login_success_redirects_to_monthly(client, create_test_user):
    create_test_user("taro", "password123")
    token = get_csrf_token(client, "/login")
    resp = client.post(
        "/login",
        data={"username": "taro", "password": "password123", "csrf_token": token},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/monthly")


def test_login_wrong_password_shows_generic_message(client, create_test_user):
    create_test_user("taro", "password123")
    token = get_csrf_token(client, "/login")
    resp = client.post(
        "/login",
        data={"username": "taro", "password": "wrong-password", "csrf_token": token},
    )
    assert "ユーザー名またはパスワードが間違っています" in resp.get_data(as_text=True)


def test_login_unknown_user_shows_same_generic_message(client):
    token = get_csrf_token(client, "/login")
    resp = client.post(
        "/login",
        data={"username": "nobody", "password": "whatever1", "csrf_token": token},
    )
    assert "ユーザー名またはパスワードが間違っています" in resp.get_data(as_text=True)


def test_login_rate_limit_locks_after_five_failures(client, create_test_user):
    create_test_user("taro", "password123")
    for _ in range(5):
        token = get_csrf_token(client, "/login")
        client.post(
            "/login",
            data={"username": "taro", "password": "wrong-password", "csrf_token": token},
        )
    token = get_csrf_token(client, "/login")
    resp = client.post(
        "/login",
        data={"username": "taro", "password": "password123", "csrf_token": token},
    )
    assert "上限を超えました" in resp.get_data(as_text=True)


def test_monthly_requires_login(client):
    resp = client.get("/monthly")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_monthly_accessible_after_login(auth_client):
    resp = auth_client.get("/monthly")
    assert resp.status_code == 200


def test_logout_requires_csrf(auth_client):
    resp = auth_client.post("/logout", data={})
    assert resp.status_code == 403


def test_logout_clears_session(auth_client):
    auth_client.get("/monthly")  # CSRFトークンをセッションに発行させる
    with auth_client.session_transaction() as sess:
        token = sess["csrf_token"]
    resp = auth_client.post("/logout", data={"csrf_token": token})
    assert resp.status_code == 302
    resp2 = auth_client.get("/monthly")
    assert resp2.status_code == 302
