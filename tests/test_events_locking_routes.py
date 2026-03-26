from fastapi.testclient import TestClient

from main import app


def _assert_redirect_to_login(resp):
    if resp.status_code in (302, 303, 307):
        return
    history = getattr(resp, "history", []) or []
    assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"


def test_events_lock_date_requires_auth():
    client = TestClient(app)
    r = client.post("/events/1/lock-date")
    _assert_redirect_to_login(r)


def test_events_lock_date_by_code_requires_auth():
    client = TestClient(app)
    r = client.post("/e/ABC123/lock-date")
    _assert_redirect_to_login(r)
