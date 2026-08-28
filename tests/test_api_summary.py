def _token(client):
    client.get("/monthly")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def _create(client, **overrides):
    payload = {
        "date": "2026-08-10",
        "type": "expense",
        "description": "取引",
        "amount": 1000,
        "csrf_token": _token(client),
    }
    payload.update(overrides)
    return client.post("/api/transactions", json=payload)


def test_monthly_stats(auth_client):
    _create(auth_client, type="income", description="給与", amount=3000)
    _create(auth_client, type="expense", description="食費", amount=1000)
    resp = auth_client.get("/api/summary?mode=monthly_stats&month=2026-08")
    data = resp.get_json()
    assert data == {"income": 3000, "expense": 1000, "balance": 2000}


def test_category_chart_unions_item_level_and_transaction_level(auth_client):
    # 内訳ありの取引: item単位のcategory_idで集計される
    _create(
        auth_client,
        amount=None,
        items=[{"item_name": "パン", "amount": 300, "category_id": 1}],
    )
    # 内訳なしの取引: 本体のcategory_idで集計される
    _create(auth_client, amount=700, category_id=1)
    # 未分類（category_id指定なし、items無し）
    _create(auth_client, amount=200)

    resp = auth_client.get("/api/summary?mode=category_chart&month=2026-08")
    data = resp.get_json()
    by_category = {row["category"]: row["value"] for row in data}
    assert by_category["食費"] == 1000
    assert by_category["未分類"] == 200


def test_payment_chart_unset_label(auth_client):
    _create(auth_client, amount=500, payment_method_id=1)
    _create(auth_client, amount=300)
    resp = auth_client.get("/api/summary?mode=payment_chart&month=2026-08")
    data = resp.get_json()
    by_payment = {row["payment_method"]: row["value"] for row in data}
    assert by_payment["現金"] == 500
    assert by_payment["未設定"] == 300


def test_annual_trend_has_twelve_months(auth_client):
    _create(auth_client, date="2026-01-15", amount=100)
    _create(auth_client, type="income", description="給与", date="2026-03-15", amount=200)
    resp = auth_client.get("/api/summary?mode=annual_trend&year=2026")
    data = resp.get_json()
    assert len(data["labels"]) == 12
    assert data["expense"][0] == 100
    assert data["income"][2] == 200


def test_summary_requires_login(client):
    resp = client.get("/api/summary?mode=monthly_stats&month=2026-08")
    assert resp.status_code == 401


def test_summary_invalid_mode(auth_client):
    resp = auth_client.get("/api/summary?mode=unknown&month=2026-08")
    assert resp.status_code == 400
