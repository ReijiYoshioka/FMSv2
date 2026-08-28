import pytest

PAGES = ["/monthly", "/graphs", "/manage", "/settings"]


@pytest.mark.parametrize("path", PAGES)
def test_page_requires_login(client, path):
    resp = client.get(path)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


@pytest.mark.parametrize("path", PAGES)
def test_page_accessible_after_login(auth_client, path):
    resp = auth_client.get(path)
    assert resp.status_code == 200
    assert 'name="csrf-token"' in resp.get_data(as_text=True)


def test_index_redirects_to_monthly(auth_client):
    resp = auth_client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/monthly")
