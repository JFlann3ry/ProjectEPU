from datetime import datetime, timezone

from app.services.auth import create_session


def test_gallery_delete_sets_deleted_and_deletedat(db_session, client):
    """Insert an event and two FileMetadata rows, call the delete endpoint and
    assert Deleted becomes True and DeletedAt is set (UTC-aware stored as naive).
    """
    from app.models.event import Event, FileMetadata
    from app.models.user import User

    # Create or reuse a user
    u = db_session.query(User).filter(User.Email == 'delete@example.test').first()
    if not u:
        u = User(
            FirstName='D', LastName='E', Email='delete@example.test',
            HashedPassword='x', IsActive=True,
        )
        db_session.add(u)
        db_session.flush()

    ev = Event(UserID=u.UserID, Name='DeleteTest', Code='DEL', Password='pw', TermsChecked=True)
    db_session.add(ev)
    db_session.flush()

    f1 = FileMetadata(EventID=ev.EventID, FileName='a.jpg', FileType='image/jpeg', FileSize=10)
    f2 = FileMetadata(EventID=ev.EventID, FileName='b.jpg', FileType='image/jpeg', FileSize=20)
    db_session.add_all([f1, f2])
    db_session.flush()

    # Ensure session and cookie
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    # Post to delete with form-encoded file_ids
    resp = client.post(
        '/gallery/actions/delete',
        data={'file_ids': [str(f1.FileMetadataID), str(f2.FileMetadataID)]},
    )
    assert resp.status_code in (200, 303)

    # Refresh objects from DB
    db_session.refresh(f1)
    db_session.refresh(f2)

    assert getattr(f1, 'Deleted', False) is True
    assert getattr(f2, 'Deleted', False) is True

    da1 = getattr(f1, 'DeletedAt', None)
    da2 = getattr(f2, 'DeletedAt', None)
    assert da1 is not None
    assert da2 is not None

    # DeletedAt should be a datetime; compare to now (allow small clock skew)
    now = datetime.now(timezone.utc)
    # If DeletedAt is naive we assume UTC (code writes timezone-aware datetime.now(timezone.utc))
    if da1.tzinfo is None:
        # treat as UTC
        da1 = da1.replace(tzinfo=timezone.utc)
    if da2.tzinfo is None:
        da2 = da2.replace(tzinfo=timezone.utc)

    assert (now - da1).total_seconds() < 60
    assert (now - da2).total_seconds() < 60
