from app.services.auth import create_session


def make_admin(db_session, email='admin-gate@example.test'):
    from app.models.user import User
    u = db_session.query(User).filter(User.Email == email).first()
    if not u:
        u = User(
            FirstName='Admin',
            LastName='Gate',
            Email=email,
            HashedPassword='x',
            IsActive=True,
            IsAdmin=True,
        )
        db_session.add(u)
        db_session.flush()
    else:
        setattr(u, 'IsAdmin', True)
        db_session.flush()
    return u


def test_debug_routes_disabled_404(monkeypatch, client, db_session):
    # Force disable flag
    import app.core.settings as core_settings
    monkeypatch.setattr(core_settings.settings, 'DEBUG_ROUTES_ENABLED', False, raising=False)

    # Auth as normal user
    from app.models.user import User
    u = db_session.query(User).filter(
        User.Email == 'user-gate@example.test'
    ).first()
    if not u:
        u = User(
            FirstName='U',
            LastName='G',
            Email='user-gate@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    # POST delete-debug should 404
    r = client.post('/gallery/actions/delete-debug', data={'file_ids': ['1','2']})
    assert r.status_code in (404, 403)

    # Admin-only GET logs should 404 even with admin when disabled
    admin = make_admin(db_session)
    sess2 = create_session(db_session, user_id=int(getattr(admin, 'UserID')))
    client.cookies.set('session_id', str(sess2.SessionID))
    r = client.get('/debug/gallery/delete_logs')
    assert r.status_code in (404, 403)


def test_debug_routes_enabled_ok(monkeypatch, client, db_session):
    import app.core.settings as core_settings
    monkeypatch.setattr(core_settings.settings, 'DEBUG_ROUTES_ENABLED', True, raising=False)

    # Normal user can call delete-debug; should 200 and return json shape
    from app.models.user import User
    u = db_session.query(User).filter(
        User.Email == 'user-gate2@example.test'
    ).first()
    if not u:
        u = User(
            FirstName='U2',
            LastName='G2',
            Email='user-gate2@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))
    r = client.post('/gallery/actions/delete-debug', data={'file_ids': ['1']})
    assert r.status_code == 200
    data = r.json()
    assert 'ok' in data

    # Admin can view logs
    admin = make_admin(db_session, email='admin-gate2@example.test')
    sess2 = create_session(db_session, user_id=int(getattr(admin, 'UserID')))
    client.cookies.set('session_id', str(sess2.SessionID))
    r = client.get('/admin/mini-dashboard')
    if r.status_code in (302, 303):
        r = client.get(r.headers.get('location'))
    assert r.status_code == 200
    text = r.text
    assert ('Raw logs (JSON)' in text) or ('debug_routes_enabled' in text)
