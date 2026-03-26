from fastapi.testclient import TestClient

from main import app


def _assert_redirect_to_login(resp):
    if resp.status_code not in (302, 303, 307):
        history = getattr(resp, "history", []) or []
        assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"
        return
    location = (resp.headers.get("location", "") or "").lower()
    if location:
        assert "/login" in location


def test_events_albums_route_requires_auth():
    client = TestClient(app)
    r = client.get("/events/1/albums")
    _assert_redirect_to_login(r)


def test_events_albums_create_requires_auth():
    client = TestClient(app)
    r = client.post("/events/1/albums/create", data={"name": "Test"})
    _assert_redirect_to_login(r)


def test_events_guestbook_delete_requires_auth():
    client = TestClient(app)
    r = client.post("/events/1/guestbook/1/delete")
    _assert_redirect_to_login(r)
