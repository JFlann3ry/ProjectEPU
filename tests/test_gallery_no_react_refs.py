from app.services.auth import create_session


def test_gallery_page_has_no_react_assets(client, db_session):
    # Create user and session
    from app.models.user import User
    u = db_session.query(User).filter(
        User.Email == 'no-react@example.test'
    ).first()
    if not u:
        u = User(
            FirstName='No',
            LastName='React',
            Email='no-react@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    r = client.get('/gallery')
    if r.status_code in (302, 303):
        r = client.get(r.headers.get('location'))
    assert r.status_code == 200
    html = r.text
    # Ensure no obvious React/Vite asset references
    forbidden = [
        '/src/main.jsx',
        'react-dom',
        '@vite',
        'vite',
        'id="root"',
        'data-reactroot',
    ]
    for frag in forbidden:
        assert frag not in html
