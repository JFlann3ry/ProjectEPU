from fastapi.testclient import TestClient

from main import app


def _assert_redirect(resp):
    if resp.status_code in (302, 303, 307):
        return
    history = getattr(resp, "history", []) or []
    assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"


def test_gallery_app_page_requires_auth():
    client = TestClient(app)
    r = client.get("/events/1/gallery/app")
    _assert_redirect(r)


def test_event_gallery_requires_auth():
    client = TestClient(app)
    r = client.get("/events/1/gallery")
    _assert_redirect(r)


def test_thumbs_requires_auth():
    client = TestClient(app)
    r = client.get("/thumbs/1.jpg")
    _assert_redirect(r)
