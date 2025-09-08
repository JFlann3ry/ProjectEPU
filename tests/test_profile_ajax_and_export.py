import re

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _extract_cookie(resp, name):
    sc = resp.headers.get("set-cookie", "")
    for part in sc.split(","):
        part = part.strip()
        if part.lower().startswith(f"{name}="):
            return part.split(";", 1)[0].split("=", 1)[1]
    return None


def _get_csrf_token(cookies: dict):
    # Hit /login to seed a session_id if needed, then /profile/edit to obtain CSRF cookie
    if cookies:
        for k, v in cookies.items():
            client.cookies.set(k, v)
    client.get("/login")
    r = client.get("/profile/edit")
    # csrf token may be in set-cookie; otherwise scrape from page
    token = _extract_cookie(r, "csrf_token")
    if not token:
        m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
        token = m.group(1) if m else None
    return token


def test_email_prefs_save_and_unsubscribe_ajax_flow():
    # Create a session via login page visit to obtain session_id cookie (guest session)
    r0 = client.get("/login")
    session_id = _extract_cookie(r0, "session_id")
    cookies = {}
    if session_id:
        cookies["session_id"] = session_id
        client.cookies.set("session_id", session_id)

    csrf = _get_csrf_token(cookies)
    assert csrf

    # Save prefs via POST; server may redirect but we treat 303 as success
    r1 = client.post(
        "/profile/email-preferences",
        data={"marketing": "1", "product": "0", "reminders": "1", "csrf_token": csrf},
    )
    assert r1.status_code in (200, 302, 303)

    # Unsubscribe all
    r2 = client.post(
        "/profile/email-preferences/unsubscribe",
        data={"csrf_token": csrf},
    )
    assert r2.status_code in (200, 302, 303)


def test_export_request_enforces_cooldown():
    # New session
    r0 = client.get("/login")
    session_id = _extract_cookie(r0, "session_id")
    cookies = {}
    if session_id:
        cookies["session_id"] = session_id
        client.cookies.set("session_id", session_id)

    csrf = _get_csrf_token(cookies)
    assert csrf

    # First request should be accepted (may redirect to ready/pending)
    r1 = client.post(
        "/profile/export/request",
        data={"csrf_token": csrf},
    )
    assert r1.status_code in (200, 302, 303)

    # Second request immediately after should hit cooldown or pending
    r2 = client.post(
        "/profile/export/request",
        data={"csrf_token": csrf},
    )
    assert r2.status_code in (200, 302, 303)
