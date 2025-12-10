from app.services.auth import create_session


def _login(db_session, client, email="gallery-smoke@example.test"):
    from app.models.user import User

    u = db_session.query(User).filter(User.Email == email).first()
    if not u:
        u = User(
            FirstName="G",
            LastName="S",
            Email=email,
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()
    sess = create_session(db_session, user_id=int(getattr(u, "UserID")))
    client.cookies.set("session_id", str(sess.SessionID))
    return u


def _mk_event(db_session, user, name="SmokeEvent"):
    from app.models.event import Event

    ev = Event(
        UserID=int(getattr(user, "UserID")),
        Name=name,
        Code="SMK",
        Password="pw",
        TermsChecked=True,
    )
    db_session.add(ev)
    db_session.flush()
    return ev


def test_gallery_renders_default(db_session, client):
    """Basic smoke: /gallery renders with core elements and no template errors."""
    _login(db_session, client)
    r = client.get("/gallery")
    # Follow simple redirects if any
    if r.status_code in (302, 303):
        r = client.get(r.headers.get("location"))
    assert r.status_code == 200
    html = r.text
    # Key containers and assets
    assert 'id="gallery"' in html and 'role="list"' in html
    assert '<meta name="csrf-token"' in html
    assert 'js/pages/gallery.js' in html  # client controller present


def test_gallery_renders_with_deleted_mode(db_session, client):
    """/gallery?show_deleted=1 should still render and expose flag in JSON payload."""
    _login(db_session, client)
    r = client.get("/gallery", params={"show_deleted": 1})
    if r.status_code in (302, 303):
        r = client.get(r.headers.get("location"))
    assert r.status_code == 200
    html = r.text
    # JSON bootstrap should include show_deleted flag
    assert 'id="gallery-data"' in html
    assert '"show_deleted": 1' in html or '"show_deleted":1' in html


def test_event_gallery_route_minimal_context_renders(db_session, client):
    """/events/{id}/gallery provides a minimal context; template must handle it."""
    user = _login(db_session, client)
    ev = _mk_event(db_session, user)
    r = client.get(f"/events/{ev.EventID}/gallery")
    assert r.status_code == 200
    html = r.text
    # Even with minimal context, the gallery container and CSRF meta should exist
    assert 'id="gallery"' in html and 'role="list"' in html
    assert '<meta name="csrf-token"' in html
