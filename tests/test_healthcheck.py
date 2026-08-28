def test_healthcheck_wrong_token_returns_404(client):
    resp = client.get("/healthcheck?token=wrong-token")
    assert resp.status_code == 404


def test_healthcheck_missing_token_returns_404(client):
    resp = client.get("/healthcheck")
    assert resp.status_code == 404


def test_healthcheck_correct_token_returns_diagnostics(client):
    resp = client.get("/healthcheck?token=test-healthcheck-token")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["database"] == "ok"
    assert data["tables"]["users"]["exists"] is True
    assert data["logs_writable"] is True
