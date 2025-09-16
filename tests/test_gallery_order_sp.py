from fastapi.testclient import TestClient

from app.services.auth import create_session


def test_event_gallery_order_respects_ordinal(db_session, client: TestClient):
    # Create a minimal user and event
    from app.models.event import Event, FileMetadata
    from app.models.photo_order import EventGalleryOrder
    from app.models.user import User

    u = db_session.query(User).filter(
        User.Email == 'gallery_test@example.test'
    ).first()
    if not u:
        u = User(
            FirstName='G',
            LastName='T',
            Email='gallery_test@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()

    ev = Event(
        EventTypeID=None,
        UserID=u.UserID,
        Name='GalleryEV',
        Code='GORDER',
        Password='pw',
        TermsChecked=True,
    )
    db_session.add(ev)
    db_session.flush()

    # Create three file metadata rows
    f1 = FileMetadata(
        EventID=ev.EventID, FileName='a.jpg', FileType='image/jpeg', FileSize=100
    )
    f2 = FileMetadata(
        EventID=ev.EventID, FileName='b.jpg', FileType='image/jpeg', FileSize=100
    )
    f3 = FileMetadata(
        EventID=ev.EventID, FileName='c.jpg', FileType='image/jpeg', FileSize=100
    )
    db_session.add_all([f1, f2, f3])
    db_session.flush()

    # Insert EventGalleryOrder entries in custom order: f2, f3, f1
    o1 = EventGalleryOrder(EventID=ev.EventID, FileMetadataID=f2.FileMetadataID, Ordinal=1)
    o2 = EventGalleryOrder(EventID=ev.EventID, FileMetadataID=f3.FileMetadataID, Ordinal=2)
    o3 = EventGalleryOrder(EventID=ev.EventID, FileMetadataID=f1.FileMetadataID, Ordinal=3)
    db_session.add_all([o1, o2, o3])
    db_session.commit()

    # Create a session cookie for the user
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    # Call the API endpoint
    r = client.get(f'/events/{ev.EventID}/gallery/order')
    assert r.status_code == 200
    j = r.json()
    assert j.get('ok') is True
    files = j.get('files') or []
    ids = [int(f['id']) for f in files]
    assert ids == [f2.FileMetadataID, f3.FileMetadataID, f1.FileMetadataID]
