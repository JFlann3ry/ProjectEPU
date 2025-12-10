from app.models.event import Event, FileMetadata
from app.models.user import User
from app.services.auth import create_session


def test_user_cannot_delete_other_users_files(db_session, client):
    # Create two users
    u1 = db_session.query(User).filter(User.Email == 'owner1@example.test').first()
    if not u1:
        u1 = User(
            FirstName='Owner', LastName='One', Email='owner1@example.test',
            HashedPassword='x', IsActive=True,
        )
        db_session.add(u1)
        db_session.flush()
    u2 = db_session.query(User).filter(User.Email == 'attacker@example.test').first()
    if not u2:
        u2 = User(
            FirstName='Att', LastName='Ack', Email='attacker@example.test',
            HashedPassword='x', IsActive=True,
        )
        db_session.add(u2)
        db_session.flush()

    ev = Event(UserID=u1.UserID, Name='Owner Event', Code='OWN', Password='pw', TermsChecked=True)
    db_session.add(ev)
    db_session.flush()

    f = FileMetadata(EventID=ev.EventID, FileName='private.jpg', FileType='image/jpeg', FileSize=10)
    db_session.add(f)
    db_session.flush()

    # Attacker session
    sess = create_session(db_session, user_id=int(getattr(u2, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    # Attempt to delete owner's file
    _ = client.post('/gallery/actions/delete', data={'file_ids': [str(f.FileMetadataID)]})
    # After request, refresh file and ensure Deleted not set
    db_session.refresh(f)
    assert getattr(f, 'Deleted', False) is False
