from io import BytesIO

from app.models.event import Event
from app.models.user import User
from app.services.auth import create_session


def _login(db_session, client, user):
    sess = create_session(db_session, user_id=int(getattr(user, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))


def _mk_user_event(db):

    u = db.query(User).filter(User.Email == 'owner-upload@example.test').first()
    if not u:
        u = User(
            FirstName='U',
            LastName='P',
            Email='owner-upload@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db.add(u)
        db.flush()
    ev = Event(
        UserID=u.UserID,
        Name='UploadTest',
        Code='UP',
        Password='pw',
        TermsChecked=True,
    )
    db.add(ev)
    db.flush()
    return u, ev


def test_owner_upload_happy_path_creates_metadata_and_file(db_session, client, tmp_path):
    from app.models.event import FileMetadata
    u, ev = _mk_user_event(db_session)
    _login(db_session, client, u)

    # Minimal valid JPEG bytes
    img_bytes = BytesIO()
    try:
        from PIL import Image

        im = Image.new('RGB', (8, 6), color=(128, 128, 128))
        im.save(img_bytes, format='JPEG')
    except Exception:
        # Fallback tiny JPEG-ish bytes
        img_bytes = BytesIO(b"\xff\xd8\xff\xdb" + (b"\x00" * 256) + b"\xff\xd9")
    img_bytes.seek(0)

    files = {'files': ('t.jpg', img_bytes, 'image/jpeg')}
    r = client.post(f"/events/{ev.EventID}/upload", files=files)
    assert r.status_code in (200, 303)

    # Verify a FileMetadata row exists
    fm = (
        db_session.query(FileMetadata)
        .filter(FileMetadata.EventID == ev.EventID)
        .order_by(FileMetadata.FileMetadataID.desc())
        .first()
    )
    assert fm is not None
    # Check file exists under storage
    import os

    path = os.path.join(
        'storage',
        str(int(getattr(u, 'UserID'))),
        str(int(getattr(ev, 'EventID'))),
        str(getattr(fm, 'FileName')),
    )
    assert os.path.exists(path)


def test_owner_upload_rejects_disallowed_type(db_session, client):
    from app.models.event import FileMetadata
    u, ev = _mk_user_event(db_session)
    _login(db_session, client, u)
    bad = BytesIO(b"not an image")
    files = {'files': ('x.txt', bad, 'text/plain')}
    # Count existing metadata rows before upload
    before = (
        db_session.query(FileMetadata)
        .filter(FileMetadata.EventID == ev.EventID)
        .count()
    )
    r = client.post(f"/events/{ev.EventID}/upload", files=files)
    # Should still redirect, but not create metadata
    assert r.status_code in (200, 303)
    after = (
        db_session.query(FileMetadata)
        .filter(FileMetadata.EventID == ev.EventID)
        .count()
    )
    assert after == before