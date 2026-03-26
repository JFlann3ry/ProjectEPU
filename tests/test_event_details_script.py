from fastapi.testclient import TestClient

from main import app


def _seed_and_login(email):
    from app.models.user import User
    from app.services.auth import create_session
    from db import SessionLocal

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.Email == email).first()
        if not u:
            u = User(
                FirstName="Detail",
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
        return c, int(getattr(u, "UserID"))
    finally:
        db.close()


def test_event_details_page_uses_extracted_script():
    from app.models.event import Event
    from db import SessionLocal

    email = "event-details-script@example.test"
    client, user_id = _seed_and_login(email)

    db = SessionLocal()
    try:
        evt = db.query(Event).filter(Event.UserID == user_id).first()
        if not evt:
            evt = Event(
                UserID=user_id,
                Name="Script Test Event",
                Code="EDTST01",
                Password="x",
                Published=False,
            )
            db.add(evt)
            db.commit()
            db.refresh(evt)
        code = str(evt.Code)
    finally:
        db.close()

    r = client.get(f"/events/code/{code}")
    assert r.status_code == 200
    assert "js/pages/event_details.js" in r.text
    assert "hydrateCountdown" not in r.text
