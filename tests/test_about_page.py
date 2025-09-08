from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_about_page_exists():
    r = client.get("/about")
    assert r.status_code == 200
    assert "About EPU" in r.text
