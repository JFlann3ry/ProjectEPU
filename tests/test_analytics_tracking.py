from fastapi.testclient import TestClient


def test_analytics_collect_returns_no_content(client: TestClient):
    r = client.get("/analytics/collect", params={"e": "landing", "path": "/", "source": "test"})
    assert r.status_code == 204


def test_base_loads_analytics_script(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "static/js/analytics.js" in r.text
