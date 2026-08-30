def _token(client):
    client.get("/monthly")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def _create_recurring(client, **overrides):
    payload = {
        "day_of_month": 25,
        "type": "expense",
        "description": "サブスク",
        "amount": 1000,
        "active": True,
        "csrf_token": _token(client),
    }
    payload.update(overrides)
    return client.post("/api/recurring", json=payload)


def test_create_and_list(auth_client):
    resp = _create_recurring(auth_client)
    assert resp.status_code == 200
    listing = auth_client.get("/api/recurring?month=2026-08").get_json()
    assert len(listing["recurring"]) == 1
    assert listing["recurring"][0]["applied_this_month"] is False


def test_create_without_active_key_defaults_to_inactive(auth_client):
    # 旧PHP版の`!empty($input['active'])`相当。activeキー省略時は無効(0)扱いになる。
    resp = _create_recurring(auth_client, active=None)
    del_payload = resp.get_json()
    assert "id" in del_payload
    apply_resp = auth_client.post(
        "/api/recurring",
        json={"action": "apply", "month": "2026-08", "csrf_token": _token(auth_client)},
    )
    assert apply_resp.get_json() == {"applied": 0, "already": 0, "total": 0}


def test_income_forces_payment_method_null(auth_client):
    resp = _create_recurring(auth_client, type="income", description="給与", payment_method_id=2)
    recurring_id = resp.get_json()["id"]
    listing = auth_client.get("/api/recurring?month=2026-08").get_json()
    item = next(r for r in listing["recurring"] if r["id"] == recurring_id)
    assert item["payment_method_id"] is None


def test_invalid_day_of_month_rejected(auth_client):
    resp = _create_recurring(auth_client, day_of_month=32)
    assert resp.status_code == 400


def test_non_numeric_day_of_month_rejected(auth_client):
    resp = _create_recurring(auth_client, day_of_month="not-a-number")
    assert resp.status_code == 400


def test_non_numeric_amount_rejected(auth_client):
    resp = _create_recurring(auth_client, amount="not-a-number")
    assert resp.status_code == 400


def test_negative_amount_rejected(auth_client):
    resp = _create_recurring(auth_client, amount=-100)
    assert resp.status_code == 400


def test_description_over_200_chars_rejected_not_500(auth_client):
    resp = _create_recurring(auth_client, description="あ" * 201)
    assert resp.status_code == 400


def test_apply_creates_transaction_and_marks_applied(auth_client):
    _create_recurring(auth_client, day_of_month=25, amount=1500)

    resp = auth_client.post(
        "/api/recurring",
        json={"action": "apply", "month": "2026-08", "csrf_token": _token(auth_client)},
    )
    data = resp.get_json()
    assert data == {"applied": 1, "already": 0, "total": 1}

    transactions = auth_client.get("/api/transactions?month=2026-08").get_json()["transactions"]
    assert len(transactions) == 1
    assert transactions[0]["amount"] == 1500
    assert transactions[0]["date"].startswith("2026-08-25")

    listing = auth_client.get("/api/recurring?month=2026-08").get_json()
    assert listing["recurring"][0]["applied_this_month"] is True


def test_apply_twice_in_same_month_prevents_duplicate(auth_client):
    _create_recurring(auth_client)

    first = auth_client.post(
        "/api/recurring",
        json={"action": "apply", "month": "2026-08", "csrf_token": _token(auth_client)},
    ).get_json()
    second = auth_client.post(
        "/api/recurring",
        json={"action": "apply", "month": "2026-08", "csrf_token": _token(auth_client)},
    ).get_json()

    assert first == {"applied": 1, "already": 0, "total": 1}
    assert second == {"applied": 0, "already": 1, "total": 1}

    transactions = auth_client.get("/api/transactions?month=2026-08").get_json()["transactions"]
    assert len(transactions) == 1


def test_apply_clamps_day_to_month_end(auth_client):
    _create_recurring(auth_client, day_of_month=31)
    auth_client.post(
        "/api/recurring",
        json={"action": "apply", "month": "2026-02", "csrf_token": _token(auth_client)},
    )
    transactions = auth_client.get("/api/transactions?month=2026-02").get_json()["transactions"]
    assert transactions[0]["date"].startswith("2026-02-28")


def test_apply_skips_inactive_templates(auth_client):
    _create_recurring(auth_client, active=False)
    resp = auth_client.post(
        "/api/recurring",
        json={"action": "apply", "month": "2026-08", "csrf_token": _token(auth_client)},
    )
    data = resp.get_json()
    assert data == {"applied": 0, "already": 0, "total": 0}


def test_delete_requires_ownership(auth_client):
    resp = _create_recurring(auth_client)
    recurring_id = resp.get_json()["id"]
    delete_resp = auth_client.delete(
        f"/api/recurring/{recurring_id}", json={"csrf_token": _token(auth_client)}
    )
    assert delete_resp.status_code == 200
    delete_again = auth_client.delete(
        f"/api/recurring/{recurring_id}", json={"csrf_token": _token(auth_client)}
    )
    assert delete_again.status_code == 404


def test_recurring_requires_login(client):
    resp = client.get("/api/recurring?month=2026-08")
    assert resp.status_code == 401


def test_create_requires_csrf(auth_client):
    resp = _create_recurring(auth_client, csrf_token="invalid-token")
    assert resp.status_code == 403


def test_delete_requires_csrf(auth_client):
    create_resp = _create_recurring(auth_client)
    recurring_id = create_resp.get_json()["id"]
    resp = auth_client.delete(
        f"/api/recurring/{recurring_id}", json={"csrf_token": "invalid-token"}
    )
    assert resp.status_code == 403
