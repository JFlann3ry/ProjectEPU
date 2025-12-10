from app.services.auth import create_session


def test_admin_mini_dashboard_requires_admin(client, db_session):
    # Create a normal user and session
    from app.models.user import User

    u = db_session.query(User).filter(User.Email == 'mini@example.test').first()
    if not u:
        u = User(
            FirstName='Mini',
            LastName='Dash',
            Email='mini@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    # Not an admin, should be forbidden or redirected
    r = client.get('/admin/mini-dashboard')
    assert r.status_code in (302, 303, 401, 403)


def test_admin_mini_dashboard_renders_when_admin(client, db_session):
    from app.models.logging import AppErrorLog
    from app.models.user import User

    # Create admin user
    admin = db_session.query(User).filter(User.Email == 'admin-mini@example.test').first()
    if not admin:
        admin = User(
            FirstName='Admin',
            LastName='Mini',
            Email='admin-mini@example.test',
            HashedPassword='x',
            IsActive=True,
            IsAdmin=True,
        )
        db_session.add(admin)
        db_session.flush()
    else:
        setattr(admin, 'IsAdmin', True)
        db_session.flush()

    # Seed one AppErrorLog row
    e = AppErrorLog(Path='/x', Method='GET', StatusCode=500, Message='boom')
    db_session.add(e)

    # Visit as admin
    sess = create_session(db_session, user_id=int(getattr(admin, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    r = client.get('/admin/mini-dashboard')
    # It should render OK (allow redirect then follow location)
    if r.status_code in (302, 303):
        r = client.get(r.headers.get('location'))
    assert r.status_code in (200,)
    text = r.text
    assert 'Admin Mini-Dashboard' in text
    assert 'Recent App Errors' in text
    assert 'Recent Delete/Restore' in text
