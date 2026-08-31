import io


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


def test_export_has_bom_and_header(auth_client):
    _create_transaction(auth_client, category_id=1, payment_method_id=1)
    resp = auth_client.get("/api/csv?month=2026-08")
    text = resp.get_data(as_text=True)
    assert text.startswith("﻿")
    assert "date,type,description,category,payment_method,amount,memo" in text
    assert "食費" in text
    assert "現金" in text


def test_export_escapes_csv_injection(auth_client):
    _create_transaction(auth_client, description="=cmd|'/c calc'!A0")
    resp = auth_client.get("/api/csv?month=2026-08")
    text = resp.get_data(as_text=True)
    assert "'=cmd" in text


def test_import_inserts_valid_rows(auth_client):
    csv_content = (
        "date,type,description,category,payment_method,amount,memo\n"
        "2026-08-01,expense,コンビニ,食費,現金,500,\n"
        "2026-08-02,income,給与,,銀行振込,3000,\n"
    )
    data = {
        "file": (io.BytesIO(csv_content.encode("utf-8")), "import.csv"),
        "csrf_token": _token(auth_client),
    }
    resp = auth_client.post("/api/csv", data=data, content_type="multipart/form-data")
    result = resp.get_json()
    assert result["inserted"] == 2
    assert result["skipped"] == 0

    listing = auth_client.get("/api/transactions?month=2026-08").get_json()
    assert len(listing["transactions"]) == 2


def test_import_same_file_twice_skips_duplicates(auth_client):
    csv_content = (
        "date,type,description,category,payment_method,amount,memo\n"
        "2026-08-01,expense,コンビニ,食費,現金,500,\n"
        "2026-08-02,income,給与,,銀行振込,3000,\n"
    )

    def _import():
        data = {
            "file": (io.BytesIO(csv_content.encode("utf-8")), "import.csv"),
            "csrf_token": _token(auth_client),
        }
        return auth_client.post(
            "/api/csv", data=data, content_type="multipart/form-data"
        ).get_json()

    first = _import()
    assert first["inserted"] == 2
    assert first["duplicates"] == 0

    second = _import()
    assert second["inserted"] == 0
    assert second["duplicates"] == 2

    listing = auth_client.get("/api/transactions?month=2026-08").get_json()
    assert len(listing["transactions"]) == 2


def test_import_skips_invalid_rows(auth_client):
    csv_content = (
        "date,type,description,category,payment_method,amount,memo\n"
        "invalid-date,expense,コンビニ,食費,現金,500,\n"
        "2026-08-02,expense,,食費,現金,500,\n"
        "2026-08-03,expense,八百屋,食費,現金,-100,\n"
    )
    data = {
        "file": (io.BytesIO(csv_content.encode("utf-8")), "import.csv"),
        "csrf_token": _token(auth_client),
    }
    resp = auth_client.post("/api/csv", data=data, content_type="multipart/form-data")
    result = resp.get_json()
    assert result["inserted"] == 0
    assert result["skipped"] == 3
    assert len(result["errors"]) == 3


def test_import_skips_blank_lines_silently(auth_client):
    csv_content = (
        "date,type,description,category,payment_method,amount,memo\n"
        "2026-08-01,expense,コンビニ,食費,現金,500,\n"
        "\n"
        "2026-08-02,income,給与,,銀行振込,3000,\n"
        "\n"
    )
    data = {
        "file": (io.BytesIO(csv_content.encode("utf-8")), "import.csv"),
        "csrf_token": _token(auth_client),
    }
    resp = auth_client.post("/api/csv", data=data, content_type="multipart/form-data")
    result = resp.get_json()
    assert result["inserted"] == 2
    assert result["skipped"] == 0
    assert result["errors"] == []


def test_import_requires_login(client):
    data = {"file": (io.BytesIO(b"date,type,description\n"), "import.csv")}
    resp = client.post("/api/csv", data=data, content_type="multipart/form-data")
    assert resp.status_code == 401


def test_import_requires_csrf(auth_client):
    data = {
        "file": (io.BytesIO(b"date,type,description\n"), "import.csv"),
        "csrf_token": "invalid-token",
    }
    resp = auth_client.post("/api/csv", data=data, content_type="multipart/form-data")
    assert resp.status_code == 403


def test_import_over_2mb_rejected_with_clean_error(auth_client):
    # csv_service.MAX_IMPORT_BYTES(2MB)を超えるが、MAX_CONTENT_LENGTH(12MB)は超えない
    # サイズにして、機能側の400エラーが先に発火することを確認する。
    big_content = "date,type,description,category,payment_method,amount,memo\n" + "a" * (
        2 * 1024 * 1024 + 100
    )
    data = {
        "file": (io.BytesIO(big_content.encode("utf-8")), "big.csv"),
        "csrf_token": _token(auth_client),
    }
    resp = auth_client.post("/api/csv", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert "2MB" in resp.get_json()["error"]
