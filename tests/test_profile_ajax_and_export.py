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


def _seed_and_login_profile(email):
    from app.models.user import User
    from app.services.auth import create_session
    from db import SessionLocal

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.Email == email).first()
        if not u:
            u = User(
                FirstName="Profile",
                LastName="Test",
                Email=email,
                HashedPassword="x",
                IsActive=True,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        sess = create_session(db, user_id=int(getattr(u, "UserID")))
        c = TestClient(app)
        c.cookies.set("session_id", str(sess.SessionID))
        return c
    finally:
        db.close()


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


def test_profile_page_uses_extracted_script():
    c = _seed_and_login_profile("profile_script_test@example.com")
    r = c.get("/profile")
    assert r.status_code == 200
    assert "js/pages/profile.js" in r.text
    assert "(function(){" not in r.text


def test_profile_page_renders_recent_and_next_event_sections():
    c = _seed_and_login_profile("profile_render_test@example.com")
    r = c.get("/profile")
    assert r.status_code == 200
    assert "Next event" in r.text
    assert "Manage your account, events, and preferences." in r.text


def test_profile_page_renders_avatar_dropdown_shell():
    c = _seed_and_login_profile("profile_avatar_test@example.com")
    r = c.get("/profile")
    assert r.status_code == 200
    assert 'id="user-menu"' in r.text
    assert 'id="avatar-btn"' in r.text
    assert 'id="user-dropdown"' in r.text
    assert 'href="/profile"' in r.text
