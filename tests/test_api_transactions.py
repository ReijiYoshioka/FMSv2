from conftest import get_csrf_token


def _token(client):
    client.get("/monthly")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def _create(client, **overrides):
    payload = {
        "date": "2026-08-10",
        "type": "expense",
        "description": "スーパー",
        "amount": 1000,
        "csrf_token": _token(client),
    }
    payload.update(overrides)
    return client.post("/api/transactions", json=payload)


def test_list_requires_login(client):
    resp = client.get("/api/transactions?month=2026-08")
    assert resp.status_code == 401


def test_metadata_returns_categories_and_payment_methods(auth_client):
    resp = auth_client.get("/api/transactions?action=metadata")
    data = resp.get_json()
    assert len(data["categories"]) == 13
    assert len(data["payment_methods"]) == 8


def test_create_without_items_uses_top_level_amount(auth_client):
    resp = _create(auth_client, amount=1500)
    assert resp.status_code == 200
    tx_id = resp.get_json()["id"]

    listing = auth_client.get("/api/transactions?month=2026-08").get_json()
    tx = next(t for t in listing["transactions"] if t["id"] == tx_id)
    assert tx["amount"] == 1500
    assert tx["items"] == []


def test_create_with_items_sums_amount(auth_client):
    resp = _create(
        auth_client,
        amount=None,
        items=[
            {"item_name": "パン", "amount": 300, "category_id": 1},
            {"item_name": "牛乳", "amount": 200, "category_id": 1},
        ],
    )
    assert resp.status_code == 200
    tx_id = resp.get_json()["id"]

    listing = auth_client.get("/api/transactions?month=2026-08").get_json()
    tx = next(t for t in listing["transactions"] if t["id"] == tx_id)
    assert tx["amount"] == 500
    assert len(tx["items"]) == 2
    # category_id未指定+items有り+expense → 最頻カテゴリー自動設定
    assert tx["category_id"] == 1


def test_income_forces_payment_method_null(auth_client):
    resp = _create(auth_client, type="income", description="給与", payment_method_id=2)
    tx_id = resp.get_json()["id"]
    listing = auth_client.get("/api/transactions?month=2026-08").get_json()
    tx = next(t for t in listing["transactions"] if t["id"] == tx_id)
    assert tx["payment_method_id"] is None


def test_description_required(auth_client):
    resp = _create(auth_client, description="  ")
    assert resp.status_code == 400


def test_negative_amount_rejected(auth_client):
    resp = _create(auth_client, amount=-100)
    assert resp.status_code == 400


def test_update_replaces_items(auth_client):
    create_resp = _create(
        auth_client,
        amount=None,
        items=[{"item_name": "パン", "amount": 300, "category_id": 1}],
    )
    tx_id = create_resp.get_json()["id"]

    update_resp = auth_client.post(
        "/api/transactions",
        json={
            "id": tx_id,
            "date": "2026-08-10",
            "type": "expense",
            "description": "スーパー(更新)",
            "items": [{"item_name": "卵", "amount": 400, "category_id": 1}],
            "csrf_token": _token(auth_client),
        },
    )
    assert update_resp.status_code == 200

    listing = auth_client.get("/api/transactions?month=2026-08").get_json()
    tx = next(t for t in listing["transactions"] if t["id"] == tx_id)
    assert tx["amount"] == 400
    assert len(tx["items"]) == 1
    assert tx["items"][0]["item_name"] == "卵"


def test_update_other_users_transaction_returns_404(auth_client, create_test_user, app):
    create_resp = _create(auth_client)
    tx_id = create_resp.get_json()["id"]

    create_test_user("jiro", "password123")
    other_client = app.test_client()
    login_token = get_csrf_token(other_client, "/login")
    other_client.post(
        "/login",
        data={"username": "jiro", "password": "password123", "csrf_token": login_token},
    )
    resp = other_client.post(
        "/api/transactions",
        json={
            "id": tx_id,
            "date": "2026-08-10",
            "type": "expense",
            "description": "乗っ取り",
            "amount": 1,
            "csrf_token": _token(other_client),
        },
    )
    assert resp.status_code == 404


def test_delete_requires_ownership(auth_client, create_test_user, app):
    create_resp = _create(auth_client)
    tx_id = create_resp.get_json()["id"]

    resp = auth_client.delete(
        f"/api/transactions/{tx_id}", json={"csrf_token": _token(auth_client)}
    )
    assert resp.status_code == 200

    resp2 = auth_client.delete(
        f"/api/transactions/{tx_id}", json={"csrf_token": _token(auth_client)}
    )
    assert resp2.status_code == 404


def test_filter_by_keyword(auth_client):
    _create(auth_client, description="コンビニ")
    _create(auth_client, description="八百屋")
    resp = auth_client.get("/api/transactions?month=2026-08&q=コンビニ")
    data = resp.get_json()
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["description"] == "コンビニ"


def test_filter_by_amount_range(auth_client):
    _create(auth_client, amount=100)
    _create(auth_client, amount=5000)
    resp = auth_client.get("/api/transactions?month=2026-08&min=1000&max=10000")
    data = resp.get_json()
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["amount"] == 5000


def test_all_time_returns_transactions_across_months(auth_client):
    _create(auth_client, date="2025-01-10", description="去年の取引")
    _create(auth_client, date="2026-08-10", description="今月の取引")
    resp = auth_client.get("/api/transactions?all_time=1")
    data = resp.get_json()
    assert resp.status_code == 200
    assert len(data["transactions"]) == 2
    assert data["truncated"] is False


def test_all_time_ignores_month_param(auth_client):
    _create(auth_client, date="2025-01-10")
    resp = auth_client.get("/api/transactions?all_time=1&month=not-a-valid-month")
    assert resp.status_code == 200


def test_month_mode_still_scoped_to_month(auth_client):
    _create(auth_client, date="2025-01-10", description="去年の取引")
    _create(auth_client, date="2026-08-10", description="今月の取引")
    resp = auth_client.get("/api/transactions?month=2026-08")
    data = resp.get_json()
    assert len(data["transactions"]) == 1
    assert data["truncated"] is False


def test_all_time_truncates_beyond_limit(auth_client, monkeypatch):
    from fmsv2.blueprints import api_transactions

    monkeypatch.setattr(api_transactions, "ALL_TIME_LIMIT", 2)
    for i in range(3):
        _create(auth_client, date=f"2026-08-{10 + i:02d}", description=f"取引{i}")
    resp = auth_client.get("/api/transactions?all_time=1")
    data = resp.get_json()
    assert len(data["transactions"]) == 2
    assert data["truncated"] is True


def test_create_requires_csrf(auth_client):
    resp = _create(auth_client, csrf_token="invalid-token")
    assert resp.status_code == 403


def test_delete_requires_csrf(auth_client):
    create_resp = _create(auth_client)
    tx_id = create_resp.get_json()["id"]
    resp = auth_client.delete(f"/api/transactions/{tx_id}", json={"csrf_token": "invalid-token"})
    assert resp.status_code == 403
