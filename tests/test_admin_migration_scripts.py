from fastapi.testclient import TestClient

from main import app


def _seed_and_login_admin(email):
    from app.models.user import User
    from app.services.auth import create_session
    from db import SessionLocal

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.Email == email).first()
        if not u:
            u = User(
                FirstName="Admin",
                LastName="Test",
                Email=email,
                HashedPassword="x",
                IsActive=True,
                IsAdmin=True,
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


def test_admin_components_page_uses_extracted_script():
    client = _seed_and_login_admin("admin-components@example.test")
    r = client.get("/admin/components")
    assert r.status_code == 200
    assert "js/pages/admin_components.js" in r.text
    assert "demoModalBtn.addEventListener" not in r.text


def test_admin_themes_page_uses_extracted_script():
    client = _seed_and_login_admin("admin-themes@example.test")
    r = client.get("/admin/themes")
    assert r.status_code == 200
    assert "js/pages/admin_themes.js" in r.text
    assert "Apply backgrounds to theme swatches" not in r.text
