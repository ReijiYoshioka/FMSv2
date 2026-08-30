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


def test_list_masters(auth_client):
    resp = auth_client.get("/api/masters")
    data = resp.get_json()
    assert len(data["categories"]) == 13
    assert len(data["payment_methods"]) == 8


def test_add_category(auth_client):
    resp = auth_client.post(
        "/api/masters",
        json={"kind": "category", "name": "新カテゴリ", "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 200
    listing = auth_client.get("/api/masters").get_json()
    assert any(c["name"] == "新カテゴリ" for c in listing["categories"])


def test_add_duplicate_category_conflicts(auth_client):
    resp = auth_client.post(
        "/api/masters",
        json={"kind": "category", "name": "食費", "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 409


def test_rename_category(auth_client):
    resp = auth_client.post(
        "/api/masters",
        json={"kind": "category", "id": 1, "name": "食費(改名)", "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 200
    listing = auth_client.get("/api/masters").get_json()
    renamed = next(c for c in listing["categories"] if c["id"] == 1)
    assert renamed["name"] == "食費(改名)"


def test_rename_nonexistent_category_returns_404(auth_client):
    resp = auth_client.post(
        "/api/masters",
        json={
            "kind": "category",
            "id": 99999,
            "name": "存在しない",
            "csrf_token": _token(auth_client),
        },
    )
    assert resp.status_code == 404


def test_delete_unused_category_succeeds(auth_client):
    add_resp = auth_client.post(
        "/api/masters",
        json={"kind": "category", "name": "未使用カテゴリ", "csrf_token": _token(auth_client)},
    )
    new_id = add_resp.get_json()["id"]
    resp = auth_client.delete(
        "/api/masters", json={"kind": "category", "id": new_id, "csrf_token": _token(auth_client)}
    )
    assert resp.status_code == 200


def test_delete_used_category_conflicts(auth_client):
    _create_transaction(auth_client, category_id=1)
    resp = auth_client.delete(
        "/api/masters", json={"kind": "category", "id": 1, "csrf_token": _token(auth_client)}
    )
    assert resp.status_code == 409


def test_delete_used_payment_method_conflicts(auth_client):
    _create_transaction(auth_client, payment_method_id=1)
    resp = auth_client.delete(
        "/api/masters", json={"kind": "payment", "id": 1, "csrf_token": _token(auth_client)}
    )
    assert resp.status_code == 409


def test_masters_requires_login(client):
    resp = client.get("/api/masters")
    assert resp.status_code == 401


def test_add_payment_method(auth_client):
    resp = auth_client.post(
        "/api/masters",
        json={"kind": "payment", "name": "新決済手段", "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 200
    listing = auth_client.get("/api/masters").get_json()
    assert any(p["name"] == "新決済手段" for p in listing["payment_methods"])


def test_add_duplicate_payment_method_conflicts(auth_client):
    resp = auth_client.post(
        "/api/masters",
        json={"kind": "payment", "name": "現金", "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 409


def test_rename_payment_method(auth_client):
    resp = auth_client.post(
        "/api/masters",
        json={"kind": "payment", "id": 1, "name": "現金(改名)", "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 200
    listing = auth_client.get("/api/masters").get_json()
    renamed = next(p for p in listing["payment_methods"] if p["id"] == 1)
    assert renamed["name"] == "現金(改名)"


def test_delete_unused_payment_method_succeeds(auth_client):
    add_resp = auth_client.post(
        "/api/masters",
        json={"kind": "payment", "name": "未使用決済手段", "csrf_token": _token(auth_client)},
    )
    new_id = add_resp.get_json()["id"]
    resp = auth_client.delete(
        "/api/masters", json={"kind": "payment", "id": new_id, "csrf_token": _token(auth_client)}
    )
    assert resp.status_code == 200


def test_invalid_kind_rejected(auth_client):
    resp = auth_client.post(
        "/api/masters",
        json={"kind": "not-a-kind", "name": "x", "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 400


def test_add_requires_csrf(auth_client):
    resp = auth_client.post(
        "/api/masters",
        json={"kind": "category", "name": "新カテゴリ", "csrf_token": "invalid-token"},
    )
    assert resp.status_code == 403


def test_delete_requires_csrf(auth_client):
    resp = auth_client.delete(
        "/api/masters", json={"kind": "category", "id": 1, "csrf_token": "invalid-token"}
    )
    assert resp.status_code == 403
