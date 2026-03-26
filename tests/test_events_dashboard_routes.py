from fastapi.testclient import TestClient

from main import app


def _assert_redirect(resp):
    if resp.status_code in (302, 303, 307):
        return
    history = getattr(resp, "history", []) or []
    assert any(h.status_code in (302, 303, 307) for h in history), "Expected redirect"


def _seed_and_login(email):
    from app.models.user import User
    from app.services.auth import create_session
    from db import SessionLocal

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.Email == email).first()
        if not u:
            u = User(
                FirstName="Dash",
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


def test_events_dashboard_requires_auth():
    client = TestClient(app)
    r = client.get("/events")
    _assert_redirect(r)


def test_events_mark_shared_requires_auth():
    client = TestClient(app)
    r = client.post("/events/1/mark-shared")
    _assert_redirect(r)


def test_public_event_share_unknown_code_404():
    client = TestClient(app)
    r = client.get("/e/DOESNOTEXIST")
    assert r.status_code == 404


def test_events_dashboard_page_uses_extracted_script():
    client = _seed_and_login("dash_test@example.com")
    r = client.get("/events")
    assert r.status_code == 200
    assert "js/pages/events_dashboard.js" in r.text
    assert "hydrateCountdown" not in r.text


def test_events_dashboard_skips_stripe_reconciliation(monkeypatch):
    from app.services import billing_utils

    client = _seed_and_login("dash_plan_test@example.com")
    called = {"reconcile": False}

    def fail_reconcile(_db, _user_id):
        called["reconcile"] = True
        raise AssertionError("dashboard should not reconcile pending Stripe purchases")

    monkeypatch.setattr(billing_utils, "_reconcile_pending_with_stripe", fail_reconcile)
    r = client.get("/events")
    assert r.status_code == 200
    assert called["reconcile"] is False


def test_events_dashboard_uses_image_tag_for_cover():
    import uuid

    from app.models.event import Event
    from db import SessionLocal

    email = "dash_cover_test@example.com"
    client = _seed_and_login(email)
    db = SessionLocal()
    try:
        from app.models.user import User

        user = db.query(User).filter(User.Email == email).first()
        event = Event(
            UserID=int(getattr(user, "UserID")),
            Name="Cover Test Event",
            Code=f"DASHCOV{uuid.uuid4().hex[:10].upper()}",
            Password="x",
            Published=False,
        )
        db.add(event)
        db.commit()
    finally:
        db.close()

    r = client.get("/events")
    assert r.status_code == 200
    assert 'loading="lazy"' in r.text
    assert 'alt="' in r.text
