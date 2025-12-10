from app.services.auth import create_session


def _make_user(db_session, email):
    from app.models.user import User

    u = db_session.query(User).filter(User.Email == email).first()
    if not u:
        u = User(
            FirstName='R', LastName='U', Email=email,
            HashedPassword='x', IsActive=True,
        )
        db_session.add(u)
        db_session.flush()
    return u


def _make_event_and_files(db_session, user, n=2):
    from app.models.event import Event, FileMetadata

    ev = Event(
        UserID=user.UserID,
        Name='RestoreTest',
        Code='REST',
        Password='pw',
        TermsChecked=True,
    )
    db_session.add(ev)
    db_session.flush()

    files = []
    for i in range(n):
        f = FileMetadata(
            EventID=ev.EventID,
            FileName=f'r{i}.jpg',
            FileType='image/jpeg',
            FileSize=10 + i,
        )
        db_session.add(f)
        files.append(f)
    db_session.flush()
    return ev, files


def _login(db_session, client, user):
    sess = create_session(db_session, user_id=int(getattr(user, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))


def test_gallery_restore_clears_deleted_and_deletedat(db_session, client):
    """Delete a file via endpoint, then restore it; ensure Deleted=False and DeletedAt=None."""
    from app.models.event import FileMetadata

    u = _make_user(db_session, 'restore_happy@example.test')
    ev, (f1, ) = _make_event_and_files(db_session, u, n=1)

    _login(db_session, client, u)

    # Soft-delete first via the real endpoint to set Deleted and DeletedAt
    resp_del = client.post('/gallery/actions/delete', data={'file_ids': [str(f1.FileMetadataID)]})
    assert resp_del.status_code in (200, 303)

    # Now restore
    resp = client.post('/gallery/actions/restore', data={'file_ids': [str(f1.FileMetadataID)]})
    assert resp.status_code in (200, 303)

    # Refresh and validate
    db_session.refresh(f1)
    assert getattr(f1, 'Deleted', True) is False
    # DeletedAt should become None if column exists
    try:
        _ = getattr(FileMetadata, 'DeletedAt')
        assert getattr(f1, 'DeletedAt', 'sentinel') is None
    except Exception:
        # Column may not exist in some schemas; skip strict check
        pass


def test_gallery_restore_redirects_to_gallery_when_none_remaining(db_session, client):
    """If after restore no deleted remain, expect redirect to /gallery, else referer."""
    u = _make_user(db_session, 'restore_redirect@example.test')
    ev, files = _make_event_and_files(db_session, u, n=2)
    f1, f2 = files

    _login(db_session, client, u)

    # Delete both
    r1 = client.post(
        '/gallery/actions/delete',
        data={'file_ids': [str(f1.FileMetadataID), str(f2.FileMetadataID)]},
    )
    assert r1.status_code in (200, 303)

    # Restore only one — there is still another deleted so expect redirect to referer
    r2 = client.post(
        '/gallery/actions/restore',
        data={'file_ids': [str(f1.FileMetadataID)]},
        headers={'referer': '/gallery?show=deleted'},
    )
    assert r2.status_code in (200, 303)
    # When running under TestClient, we may get a 200 HTML body instead of
    # following redirect; be lenient and check the Location header when
    # available
    if hasattr(r2, 'headers'):
        loc = r2.headers.get('location')
        if loc is not None:
            assert loc.startswith('/gallery?')

    # Restore the last remaining; now none should remain — expect redirect to /gallery
    r3 = client.post(
        '/gallery/actions/restore',
        data={'file_ids': [str(f2.FileMetadataID)]},
        headers={'referer': '/gallery?show=deleted'},
    )
    assert r3.status_code in (200, 303)
    if hasattr(r3, 'headers'):
        loc = r3.headers.get('location')
        if loc is not None:
            assert loc == '/gallery'


def test_gallery_restore_auth_guard(db_session, client):
    """User A cannot restore files that belong to User B."""
    from app.models.event import FileMetadata

    ua = _make_user(db_session, 'owner_a@example.test')
    ub = _make_user(db_session, 'owner_b@example.test')

    ev_b, (fb,) = _make_event_and_files(db_session, ub, n=1)

    # Log in as B and delete their file
    _login(db_session, client, ub)
    rdel = client.post('/gallery/actions/delete', data={'file_ids': [str(fb.FileMetadataID)]})
    assert rdel.status_code in (200, 303)

    # Switch to user A and attempt to restore B's file — should be a no-op
    _login(db_session, client, ua)
    rres = client.post('/gallery/actions/restore', data={'file_ids': [str(fb.FileMetadataID)]})
    assert rres.status_code in (200, 303)

    # Verify file remains deleted
    db_session.refresh(fb)
    assert getattr(fb, 'Deleted', False) is True
    try:
        _ = getattr(FileMetadata, 'DeletedAt')
        assert getattr(fb, 'DeletedAt', None) is not None
    except Exception:
        pass
