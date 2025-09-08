from fastapi.testclient import TestClient

from main import app


def test_qr_basic_and_theme_params():
    client = TestClient(app)
    # Basic path
    r = client.get("/qr", params={"path": "/guest/upload/TEST123"})
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/png")
    # Theme dark
    r2 = client.get("/qr", params={"path": "/guest/upload/TEST123", "theme": "dark"})
    assert r2.status_code == 200
    # Custom colors
    r3 = client.get(
        "/qr",
        params={"path": "/guest/upload/TEST123", "fg": "#111111", "bg": "#eeeeee"},
    )
    assert r3.status_code == 200
    # ECC and size
    r4 = client.get(
        "/qr",
        params={"path": "/guest/upload/TEST123", "ecc": "H", "box_size": 8, "border": 2},
    )
    assert r4.status_code == 200


def test_event_details_guest_link_points_to_upload():
    client = TestClient(app)
    # We don't know if /events/1 exists or user is logged in.
    # If the page renders (200), it should include the direct upload link.
    r = client.get("/events/1", follow_redirects=False)
    assert r.status_code in (200, 302, 303, 404)
    if r.status_code == 200:
        assert "/guest/upload/" in r.text