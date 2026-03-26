import io

from fastapi.testclient import TestClient

from main import app


def _assert_redirect(resp):
    if resp.status_code in (302, 303, 307):
        return
    history = getattr(resp, "history", []) or []
    assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"


def test_events_qr_logo_route_requires_auth():
    client = TestClient(app)
    files = {"file": ("logo.png", io.BytesIO(b"not-an-image"), "image/png")}
    r = client.post("/events/1/qr/logo", files=files)
    _assert_redirect(r)


def test_events_banner_route_requires_auth():
    client = TestClient(app)
    files = {"file": ("banner.png", io.BytesIO(b"not-an-image"), "image/png")}
    r = client.post("/events/1/banner", files=files)
    _assert_redirect(r)
