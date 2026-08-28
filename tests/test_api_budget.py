def _token(client):
    client.get("/monthly")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def _create_transaction(client, **overrides):
    payload = {
        "date": "2026-08-10",
        "type": "expense",
        "description": "取引",
        "amount": 1000,
        "csrf_token": _token(client),
    }
    payload.update(overrides)
    return client.post("/api/transactions", json=payload)


def _save_budget(client, month, category_id, amount):
    return client.post(
        "/api/budget",
        json={
            "month": month,
            "category_id": category_id,
            "amount": amount,
            "csrf_token": _token(client),
        },
    )


def test_save_single_and_get_status(auth_client):
    resp = _save_budget(auth_client, "2026-08", 1, 5000)
    assert resp.status_code == 200

    _create_transaction(auth_client, amount=2000, category_id=1)

    status = auth_client.get("/api/budget?month=2026-08").get_json()
    item = next(i for i in status["items"] if i["category_id"] == 1)
    assert item["budget"] == 5000
    assert item["spent"] == 2000
    assert item["remaining"] == 3000
    assert item["ratio"] == 40


def test_save_zero_amount_deletes_budget(auth_client):
    _save_budget(auth_client, "2026-08", 1, 5000)
    _save_budget(auth_client, "2026-08", 1, 0)
    status = auth_client.get("/api/budget?month=2026-08").get_json()
    assert all(i["category_id"] != 1 for i in status["items"])


def test_save_items_bulk(auth_client):
    resp = auth_client.post(
        "/api/budget",
        json={
            "month": "2026-08",
            "items": [
                {"category_id": 1, "amount": 3000},
                {"category_id": 2, "amount": 4000},
            ],
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 200
    status = auth_client.get("/api/budget?month=2026-08").get_json()
    assert len(status["items"]) == 2
    assert status["total_budget"] == 7000


def test_copy_prev_month(auth_client):
    _save_budget(auth_client, "2026-07", 1, 5000)
    resp = auth_client.post(
        "/api/budget",
        json={"month": "2026-08", "action": "copy_prev", "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 200
    status = auth_client.get("/api/budget?month=2026-08").get_json()
    item = next(i for i in status["items"] if i["category_id"] == 1)
    assert item["budget"] == 5000


def test_delete_budget(auth_client):
    _save_budget(auth_client, "2026-08", 1, 5000)
    resp = auth_client.delete(
        "/api/budget",
        json={"month": "2026-08", "category_id": 1, "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 200
    resp2 = auth_client.delete(
        "/api/budget",
        json={"month": "2026-08", "category_id": 1, "csrf_token": _token(auth_client)},
    )
    assert resp2.status_code == 404


def test_budget_requires_login(client):
    resp = client.get("/api/budget?month=2026-08")
    assert resp.status_code == 401


def test_save_single_negative_amount_rejected(auth_client):
    resp = _save_budget(auth_client, "2026-08", 1, -100)
    assert resp.status_code == 400
    status = auth_client.get("/api/budget?month=2026-08").get_json()
    assert all(i["category_id"] != 1 for i in status["items"])


def test_save_items_skips_invalid_elements_without_crashing(auth_client):
    resp = auth_client.post(
        "/api/budget",
        json={
            "month": "2026-08",
            "items": [
                {"category_id": 1, "amount": 3000},
                {"category_id": "not-a-number", "amount": 4000},
                {"amount": 1000},
                {"category_id": 2, "amount": -500},
                {"category_id": 3},
            ],
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 200
    # category_id=3の要素はamount省略→0扱い(削除の空振り)として処理数に数える。旧PHP版と同じ挙動。
    assert resp.get_json()["saved"] == 2
    status = auth_client.get("/api/budget?month=2026-08").get_json()
    assert [i["category_id"] for i in status["items"]] == [1]


def test_ratio_is_zero_when_budget_not_positive(auth_client):
    _create_transaction(auth_client, amount=500, category_id=1)
    resp = auth_client.post(
        "/api/budget",
        json={
            "month": "2026-08",
            "items": [{"category_id": 1, "amount": 3000}],
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 200
    # amount=0はDELETE扱いなので、budgetsテーブルに負の値を直接書き込んで
    # ratio計算がbudget<=0を弾くことを確認する（0除算・負のratioを防ぐ回帰テスト）
    with auth_client.application.app_context():
        from fmsv2.db import get_db

        db = get_db()
        db.execute(
            "UPDATE budgets SET amount = -1000 "
            "WHERE user_id = 1 AND category_id = 1 AND month = '2026-08'"
        )
        db.commit()
    status = auth_client.get("/api/budget?month=2026-08").get_json()
    item = next(i for i in status["items"] if i["category_id"] == 1)
    assert item["ratio"] == 0


def test_total_spent_excludes_categories_without_budget(auth_client):
    _create_transaction(auth_client, amount=500, category_id=1)
    _create_transaction(auth_client, amount=2000, category_id=2)
    _save_budget(auth_client, "2026-08", 1, 1000)
    status = auth_client.get("/api/budget?month=2026-08").get_json()
    assert status["total_spent"] == 500
