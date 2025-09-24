from fastapi.testclient import TestClient

from app.services.auth import create_session


def test_event_gallery_order_partial_ordinals(db_session, client: TestClient):
    # Create a minimal user and event
    from app.models.event import Event, FileMetadata
    from app.models.photo_order import EventGalleryOrder
    from app.models.user import User

    u = db_session.query(User).filter(
        User.Email == 'gallery_edge@example.test'
    ).first()
    if not u:
        u = User(
            FirstName='G',
            LastName='E',
            Email='gallery_edge@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()

    ev = Event(
        EventTypeID=None,
        UserID=u.UserID,
        Name='GalleryEdge',
        Code='GEDGE',
        Password='pw',
        TermsChecked=True,
    )
    db_session.add(ev)
    db_session.flush()

    # Create four file metadata rows (their DB insert order will be the fallback)
    f1 = FileMetadata(EventID=ev.EventID, FileName='1.jpg', FileType='image/jpeg', FileSize=100)
    f2 = FileMetadata(EventID=ev.EventID, FileName='2.jpg', FileType='image/jpeg', FileSize=100)
    f3 = FileMetadata(EventID=ev.EventID, FileName='3.jpg', FileType='image/jpeg', FileSize=100)
    f4 = FileMetadata(EventID=ev.EventID, FileName='4.jpg', FileType='image/jpeg', FileSize=100)
    db_session.add_all([f1, f2, f3, f4])
    db_session.flush()

    # Insert EventGalleryOrder entries only for f3 and f1 (custom order: f3 then f1)
    o1 = EventGalleryOrder(EventID=ev.EventID, FileMetadataID=f3.FileMetadataID, Ordinal=1)
    o2 = EventGalleryOrder(EventID=ev.EventID, FileMetadataID=f1.FileMetadataID, Ordinal=2)
    db_session.add_all([o1, o2])
    db_session.commit()

    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    r = client.get(f'/events/{ev.EventID}/gallery/order')
    assert r.status_code == 200
    j = r.json()
    assert j.get('ok') is True
    files = j.get('files') or []
    ids = [int(f['id']) for f in files]

    # Expect the explicitly ordered ones first (f3, f1), then the remaining files
    # The remaining should preserve the fallback order produced by _build_gallery_files
    # which in absence of capture dates falls back to insertion/upload order (f2 then f4 here)
    assert ids[:2] == [f3.FileMetadataID, f1.FileMetadataID]
    assert set(ids[2:]) == {f2.FileMetadataID, f4.FileMetadataID}
