from fastapi.testclient import TestClient

from main import app


def _assert_redirect(resp):
    if resp.status_code in (302, 303, 307):
        return
    history = getattr(resp, "history", []) or []
    assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"


def test_gallery_select_requires_auth():
    client = TestClient(app)
    r = client.post("/gallery/select", data={"event_id": "1"})
    _assert_redirect(r)


def test_gallery_clear_requires_auth():
    client = TestClient(app)
    r = client.post("/gallery/clear")
    _assert_redirect(r)
