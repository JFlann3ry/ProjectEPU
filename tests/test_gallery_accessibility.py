from app.services.auth import create_session


def _login_test_user(db_session, client, email='a11y@example.test'):
    from app.models.user import User
    u = db_session.query(User).filter(User.Email == email).first()
    if not u:
        u = User(FirstName='A11y', LastName='User', Email=email, HashedPassword='x', IsActive=True)
        db_session.add(u)
        db_session.flush()
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))


def test_gallery_has_roles_and_focusability(client, db_session):
    _login_test_user(db_session, client)
    r = client.get('/gallery')
    if r.status_code in (302, 303):
        r = client.get(r.headers.get('location'))
    assert r.status_code == 200
    html = r.text
    # Container has list role, tiles have listitem and are keyboard-focusable
    assert 'id="gallery"' in html and 'role="list"' in html
    assert 'role="listitem"' in html
    assert 'tabindex="0"' in html


def test_gallery_loader_and_end_have_status_roles(client, db_session):
    _login_test_user(db_session, client)
    r = client.get('/gallery')
    if r.status_code in (302, 303):
        r = client.get(r.headers.get('location'))
    assert r.status_code == 200
    html = r.text
    assert 'id="gallery-loader"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert 'id="gallery-end"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html


def test_gallery_filter_pills_have_aria_pressed(client, db_session):
    _login_test_user(db_session, client)
    r = client.get('/gallery')
    if r.status_code in (302, 303):
        r = client.get(r.headers.get('location'))
    assert r.status_code == 200
    html = r.text
    # At least one pill should include aria-pressed="true" or "false"
    assert 'class="pill-filter"' in html
    has_true = 'aria-pressed="true"' in html
    has_false = 'aria-pressed="false"' in html
    assert has_true or has_false


def test_create_album_modal_dialog_markup(client, db_session):
    _login_test_user(db_session, client)
    r = client.get('/gallery')
    if r.status_code in (302, 303):
        r = client.get(r.headers.get('location'))
    assert r.status_code == 200
    html = r.text
    assert 'id="create-album-modal"' in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'id="create-album-cancel"' in html
