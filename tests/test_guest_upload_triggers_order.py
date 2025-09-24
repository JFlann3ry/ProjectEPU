import io

from fastapi.testclient import TestClient

from app.models.event import Event
from app.models.photo_order import EventGalleryOrder
from app.models.user import User


def test_guest_upload_creates_order(db_session, client: TestClient, tmp_path):
    # Create a minimal user and event
    u = db_session.query(User).filter(
        User.Email == 'guest_order@example.test'
    ).first()
    if not u:
        u = User(
            FirstName='G',
            LastName='O',
            Email='guest_order@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()

    ev = Event(
        EventTypeID=None,
        UserID=u.UserID,
        Name='GuestOrderTest',
        Code='GORDER',
        Password='pw',
        TermsChecked=True,
        Published=True,
    )
    db_session.add(ev)
    db_session.flush()

    # Prepare a small JPEG-like bytes payload
    img = b'\xff\xd8\xff\xdb' + (b'0' * 1024) + b'\xff\xd9'
    files = {'files': ('test.jpg', io.BytesIO(img), 'image/jpeg')}

    r = client.post(f'/guest/upload/{ev.Code}', files=files)
    assert r.status_code in (200, 303)

    # Check that FileMetadata rows exist for the event
    orders = (
        db_session.query(EventGalleryOrder)
        .filter(EventGalleryOrder.EventID == ev.EventID)
        .all()
    )
    assert len(orders) >= 1
