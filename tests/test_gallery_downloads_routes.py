from fastapi.testclient import TestClient

from main import app


def _assert_redirect(resp):
    if resp.status_code in (302, 303, 307):
        return
    history = getattr(resp, "history", []) or []
    assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"


def test_gallery_download_zip_requires_auth():
    client = TestClient(app)
    r = client.post("/gallery/download-zip", data={"file_ids": [1]})
    _assert_redirect(r)
