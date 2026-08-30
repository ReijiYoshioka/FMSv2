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


def test_empty_string_date_is_rejected_not_defaulted(auth_client):
    resp = _create(auth_client, date="")
    assert resp.status_code == 400


def test_iso8601_date_with_timezone_offset_is_accepted(auth_client):
    resp = _create(auth_client, date="2026-08-10T10:00:00+09:00")
    assert resp.status_code == 200


def test_items_not_a_list_is_treated_as_empty(auth_client):
    resp = _create(auth_client, amount=1000, items="not-a-list")
    assert resp.status_code == 200


def test_items_element_not_a_dict_returns_400(auth_client):
    resp = _create(auth_client, amount=None, items=["not-a-dict"])
    assert resp.status_code == 400


def test_boolean_amount_rejected(auth_client):
    resp = _create(auth_client, amount=True)
    assert resp.status_code == 400


def test_nan_amount_rejected_not_crashed(auth_client):
    resp = auth_client.post(
        "/api/transactions",
        json={
            "date": "2026-08-10",
            "type": "expense",
            "description": "取引",
            "amount": float("nan"),
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 400


def test_infinity_amount_rejected_not_crashed(auth_client):
    resp = auth_client.post(
        "/api/transactions",
        json={
            "date": "2026-08-10",
            "type": "expense",
            "description": "取引",
            "amount": float("inf"),
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 400


def test_item_boolean_amount_rejected(auth_client):
    resp = _create(
        auth_client,
        amount=None,
        items=[{"item_name": "パン", "amount": True, "category_id": 1}],
    )
    assert resp.status_code == 400


def test_item_non_numeric_category_id_rejected(auth_client):
    resp = _create(
        auth_client,
        amount=None,
        items=[{"item_name": "パン", "amount": 300, "category_id": "abc"}],
    )
    assert resp.status_code == 400


def test_invalid_type_filter_is_ignored_returns_all(auth_client):
    _create(auth_client, type="expense", description="A")
    _create(auth_client, type="income", description="B")
    resp = auth_client.get("/api/transactions?month=2026-08&type=not-a-type")
    data = resp.get_json()
    assert len(data["transactions"]) == 2


def test_whitespace_only_query_is_ignored(auth_client):
    _create(auth_client, description="コンビニ")
    resp = auth_client.get("/api/transactions?month=2026-08&q=%20")
    data = resp.get_json()
    assert len(data["transactions"]) == 1


def test_decimal_string_min_max_is_truncated_and_applied(auth_client):
    _create(auth_client, amount=100)
    _create(auth_client, amount=5000)
    resp = auth_client.get("/api/transactions?month=2026-08&min=1000.9&max=10000.9")
    data = resp.get_json()
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["amount"] == 5000


def test_amount_exceeding_max_rejected_not_corrupted(auth_client):
    resp = _create(auth_client, amount=1e20)
    assert resp.status_code == 400


def test_description_over_200_chars_rejected_not_500(auth_client):
    resp = _create(auth_client, description="あ" * 201)
    assert resp.status_code == 400


def test_description_exactly_200_chars_accepted(auth_client):
    resp = _create(auth_client, description="あ" * 200)
    assert resp.status_code == 200


def test_item_name_over_200_chars_rejected_not_500(auth_client):
    resp = _create(
        auth_client,
        amount=None,
        items=[{"item_name": "あ" * 201, "amount": 100, "category_id": None}],
    )
    assert resp.status_code == 400


def test_invalid_top_level_category_id_falls_back_to_none(auth_client):
    resp = _create(auth_client, category_id="not-a-number")
    assert resp.status_code == 200
    tx_id = resp.get_json()["id"]
    listing = auth_client.get("/api/transactions?month=2026-08").get_json()
    tx = next(t for t in listing["transactions"] if t["id"] == tx_id)
    assert tx["category_id"] is None
