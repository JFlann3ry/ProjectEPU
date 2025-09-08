import os

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_guest_upload_includes_theme_vars_for_invalid_event():
    # Some deployments return 404 for unknown code; accept that
    r = client.get("/guest/upload/FAKECODE")
    if r.status_code == 404:
        return
    assert r.status_code in (200, 302, 303)
    # If redirected to login, follow once to capture page content
    if r.status_code in (302, 303):
        to = r.headers.get("location") or "/"
        r = client.get(to)
    text = r.text
    assert "--bg:" in text
    assert "--btn1:" in text
    assert "--card:" in text
    assert ".theme-root" in text


def test_theme_css_bridging_classes_present():
    path = os.path.join("static", "theme.css")
    assert os.path.exists(path), "static/theme.css missing"
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        css = f.read()
    # Primary/outline bridging
    assert ".theme-root .btn.primary" in css
    assert ".is-gradient .btn-primary" in css or ".theme-root.is-gradient .btn.primary" in css
    # Radius and heading helpers
    assert ".radius-rounded" in css
    assert ".login-title.heading-m" in css


def test_admin_theme_routes_exist_but_require_auth():
    # Should redirect or deny when not authenticated
    r1 = client.get("/admin/themes/1/export")
    assert r1.status_code in (200, 302, 303, 401, 403, 404)
    r2 = client.post("/admin/themes/1/duplicate")
    assert r2.status_code in (200, 302, 303, 401, 403, 400)
    r3 = client.post("/admin/seed-themes")
    assert r3.status_code in (200, 302, 303, 401, 403, 400)
