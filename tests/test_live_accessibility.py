from fastapi.testclient import TestClient

from app.models.event import Event


def _ensure_published_event(db_session) -> Event:
    e = Event(
        UserID=1,
        Name="A11y Live Event",
        Code="A11Y01",
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
