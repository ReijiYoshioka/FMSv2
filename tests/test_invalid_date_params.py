def _token(client):
    client.get("/monthly")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def test_summary_malformed_month_returns_400_not_500(auth_client):
    resp = auth_client.get("/api/summary?mode=monthly_stats&month=not-a-month")
    assert resp.status_code == 400


def test_summary_malformed_year_returns_400_not_500(auth_client):
    resp = auth_client.get("/api/summary?mode=annual_stats&year=abcd")
    assert resp.status_code == 400


def test_budget_malformed_month_returns_400_not_500(auth_client):
    resp = auth_client.get("/api/budget?month=not-a-month")
    assert resp.status_code == 400


def test_recurring_malformed_month_returns_400_not_500(auth_client):
    resp = auth_client.get("/api/recurring?month=not-a-month")
    assert resp.status_code == 400


def test_recurring_apply_malformed_month_returns_400_not_500(auth_client):
    resp = auth_client.post(
        "/api/recurring",
        json={"action": "apply", "month": "not-a-month", "csrf_token": _token(auth_client)},
    )
    assert resp.status_code == 400


def test_csv_export_malformed_month_returns_400_not_500(auth_client):
    resp = auth_client.get("/api/csv?month=not-a-month")
    assert resp.status_code == 400
