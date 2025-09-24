import os

from app.services.auth import create_session


def test_thumb_lqip_generation(db_session, client, tmp_path):
    from app.models.event import Event, FileMetadata
    from app.models.user import User

    # Create user and event
    u = db_session.query(User).filter(User.Email == 'lqip@example.test').first()
    if not u:
        u = User(
            FirstName='L',
            LastName='Q',
            Email='lqip@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()

    ev = Event(
        UserID=u.UserID,
        Name='LQIPTest',
        Code='LQIP',
        Password='pw',
        TermsChecked=True,
    )
    db_session.add(ev)
    db_session.flush()

    # Insert a FileMetadata row
    f = FileMetadata(
        EventID=ev.EventID,
        FileName='lqip_test.jpg',
        FileType='image/jpeg',
        FileSize=10,
    )
    db_session.add(f)
    db_session.flush()

    # Ensure storage path exists and place a tiny JPEG file
    storage_dir = os.path.join('storage', str(u.UserID), str(ev.EventID))
    os.makedirs(storage_dir, exist_ok=True)
    orig_path = os.path.join(storage_dir, str(f.FileName))
    # write minimal JPEG-ish bytes
    with open(orig_path, 'wb') as fh:
        fh.write(b'\xff\xd8\xff\xdb' + (b'0' * 1024) + b'\xff\xd9')

    # Set session cookie and call thumb endpoint
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    resp = client.get(f'/thumbs/{f.FileMetadataID}.jpg?w=40&blur=5')
    assert resp.status_code == 200

    # Check that the LQIP file was created
    fid = int(getattr(f, 'FileMetadataID'))
    thumb_path = os.path.join(storage_dir, 'thumbnails', f'{fid}_40.jpg')
    assert os.path.exists(thumb_path)
