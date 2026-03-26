from fastapi.testclient import TestClient

from main import app


def _assert_redirect(resp):
    if resp.status_code in (302, 303, 307):
        return
    history = getattr(resp, "history", []) or []
    assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"


def test_gallery_delete_requires_auth():
    client = TestClient(app)
    r = client.post("/gallery/actions/delete", data={"file_ids": ["1"]})
    _assert_redirect(r)


def test_gallery_restore_requires_auth():
    client = TestClient(app)
    r = client.post("/gallery/actions/restore", data={"file_ids": ["1"]})
    _assert_redirect(r)


def test_gallery_permadelete_requires_auth():
    client = TestClient(app)
    r = client.post("/gallery/actions/permadelete", data={"file_ids": ["1"]})
    _assert_redirect(r)


def test_gallery_delete_debug_requires_auth():
    client = TestClient(app)
    r = client.post("/gallery/actions/delete-debug", data={"file_ids": ["1"]})
    _assert_redirect(r)


def test_debug_gallery_delete_logs_requires_auth():
    client = TestClient(app)
    r = client.get("/debug/gallery/delete_logs")
    _assert_redirect(r)
