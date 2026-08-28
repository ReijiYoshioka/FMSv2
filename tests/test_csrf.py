from conftest import get_csrf_token


def test_login_rejects_missing_csrf_token(client, create_test_user):
    create_test_user("taro", "password123")
    resp = client.post("/login", data={"username": "taro", "password": "password123"})
    assert "CSRFトークンが不正です" in resp.get_data(as_text=True)


def test_login_rejects_wrong_csrf_token(client, create_test_user):
    create_test_user("taro", "password123")
    get_csrf_token(client, "/login")
    resp = client.post(
        "/login",
        data={
            "username": "taro",
            "password": "password123",
            "csrf_token": "wrong-token-value",
        },
    )
    assert "CSRFトークンが不正です" in resp.get_data(as_text=True)


def test_register_rejects_wrong_csrf_token(client):
    get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={
            "username": "hanako",
            "password": "password123",
            "csrf_token": "wrong-token-value",
        },
    )
    assert "CSRFトークンが不正です" in resp.get_data(as_text=True)
