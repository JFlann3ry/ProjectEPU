from fastapi.testclient import TestClient

from main import app


def _assert_redirect(resp):
    if resp.status_code in (302, 303, 307):
        return
    history = getattr(resp, "history", []) or []
    assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"


def test_gallery_favorite_requires_auth():
    client = TestClient(app)
    r = client.post("/gallery/favorite", data={"file_id": 1})
    _assert_redirect(r)


def test_gallery_unfavorite_requires_auth():
    client = TestClient(app)
    r = client.post("/gallery/unfavorite", data={"file_id": 1})
    _assert_redirect(r)


def test_gallery_presigned_url_requires_auth():
    client = TestClient(app)
    r = client.get("/files/s3/1/presigned-url")
    _assert_redirect(r)
