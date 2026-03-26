import uuid

from fastapi.testclient import TestClient

from app.models.event import Event
from app.models.user import User


def _ensure_published_event(db_session) -> Event:
    user = db_session.query(User).filter(User.Email == "live-a11y@example.test").first()
    if not user:
        user = User(
            FirstName="Live",
            LastName="A11y",
            Email="live-a11y@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    e = Event(
        UserID=int(getattr(user, "UserID")),
        Name="A11y Live Event",
        Code=f"A11Y{uuid.uuid4().hex[:6].upper()}",
        Password="x",
        Published=True,
        TermsChecked=True,
    )
    db_session.add(e)
    db_session.flush()
    return e


def test_live_page_has_hud_and_meta(client: TestClient, db_session):
    e = _ensure_published_event(db_session)
    r = client.get(f"/live/{e.Code}")
    assert r.status_code == 200
    html = r.text
    # HUD role group for controls
    assert 'role="group"' in html and 'aria-label="Slideshow controls"' in html
    # Expected controls present by id
    for control_id in ("prev", "play", "pause", "next", "inc", "dec", "fs"):
        assert f'id="{control_id}"' in html
    # Focus-visible styling present for accessibility on dark HUD
    assert ".hud button:focus-visible" in html
    # Reduced motion media query present
    assert "prefers-reduced-motion" in html
    # SEO noindex
    assert '<meta name="robots" content="noindex"' in html
