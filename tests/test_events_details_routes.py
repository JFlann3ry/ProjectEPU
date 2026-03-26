from fastapi.testclient import TestClient

from main import app


def _assert_redirect(resp):
    if resp.status_code in (302, 303, 307):
        return
    history = getattr(resp, "history", []) or []
    assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"


def test_event_details_by_id_requires_auth():
    client = TestClient(app)
    r = client.get("/events/1")
    _assert_redirect(r)


def test_event_details_by_code_requires_auth():
    client = TestClient(app)
    r = client.get("/events/code/ABC123")
    _assert_redirect(r)
