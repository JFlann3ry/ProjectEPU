from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_login_rate_limiting(monkeypatch):
    # Force authenticate_user to always fail to trigger rate limiting
    from app.services import auth as auth_service

    def fake_auth(db, email, password):
        return None

    monkeypatch.setattr(auth_service, "authenticate_user", fake_auth)

    # Hit the endpoint RATE_LIMIT_LOGIN_ATTEMPTS times quickly
    attempts = int(getattr(auth_service.settings, "RATE_LIMIT_LOGIN_ATTEMPTS", 5))
    for _ in range(attempts):
        r = client.post("/auth/login", data={"email": "no@user", "password": "x"})
        assert r.status_code in (200, 302, 303)
    # Next attempt should be rate limited (rendering login with error)
    r = client.post("/auth/login", data={"email": "no@user", "password": "x"})
    assert r.status_code == 200
    assert "Too many login attempts" in r.text


def test_session_rotation_on_login(monkeypatch):
    # Create a fake user and sessions in-memory
    from types import SimpleNamespace  # noqa: E402

    from app.services import auth as auth_service  # noqa: E402

    fake_user = SimpleNamespace(UserID=1, EmailVerified=True)

    def fake_auth(db, email, password):
        return fake_user

    def fake_create_session(db, user_id, expires_in_minutes=60 * 24, ip_address="", user_agent=""):
        s = SimpleNamespace(SessionID="11111111-1111-1111-1111-111111111111")
        return s

    def fake_rotate_session(db, old_session_id, user_id, ip_address="", user_agent=""):
        s = SimpleNamespace(SessionID="22222222-2222-2222-2222-222222222222")
        return s

    monkeypatch.setattr(auth_service, "authenticate_user", fake_auth)
    monkeypatch.setattr(auth_service, "create_session", fake_create_session)
    monkeypatch.setattr(auth_service, "rotate_session", fake_rotate_session)

    # First login: no cookie -> create_session
    r1 = client.post("/auth/login", data={"email": "user@example.com", "password": "ok"})
    assert r1.status_code in (200, 302, 303)
    sc = r1.headers.get("set-cookie", "")
    assert "session_id=" in sc

    # Second login: send prior cookie -> rotate_session used
    cookies = {}
    for part in sc.split(";"):
        if part.strip().startswith("session_id="):
            cookies["session_id"] = part.strip().split("=", 1)[1]
    if "session_id" in cookies:
        client.cookies.set("session_id", cookies["session_id"])
    r2 = client.post(
        "/auth/login", data={"email": "user@example.com", "password": "ok"}
    )
    assert r2.status_code in (200, 302, 303)
    sc2 = r2.headers.get("set-cookie", "")
    assert "session_id=" in sc2
    # Should be a different session id suffix according to fake IDs
    assert "2222" in sc2 or sc2 != sc
