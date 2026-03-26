from fastapi.testclient import TestClient

from main import app


def test_legacy_addons_redirects_to_extras():
    """Verify /addons legacy route redirects to /extras with 307 status."""
    client = TestClient(app)
    r = client.get("/addons", follow_redirects=False)
    assert r.status_code in (301, 302, 307)
    location = r.headers.get("location", "")
    assert "/extras" in location


def test_legacy_addons_redirect_preserves_query_string():
    """Verify /addons redirect preserves query string parameters."""
    client = TestClient(app)
    r = client.get("/addons?plan=premium", follow_redirects=False)
    assert r.status_code in (301, 302, 307)
    location = r.headers.get("location", "")
    assert "/extras" in location
    assert "plan=premium" in location
