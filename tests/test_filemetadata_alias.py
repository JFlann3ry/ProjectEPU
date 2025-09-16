from app.models.event import Event, FileMetadata
from app.models.user import User


def test_fileid_synonym(db_session):
    # Ensure a User exists and create an Event referencing that user to satisfy FK constraints
    u = User(
        FirstName='FM',
        LastName='Test',
        Email='fmfiletest@example.test',
        HashedPassword='x',
        IsActive=True,
    )
    db_session.add(u)
    db_session.flush()

    e = Event(
        EventTypeID=None,
        UserID=u.UserID,
        Name='T',
        Code='FMTEST',
        Password='pw',
        TermsChecked=True,
    )
    db_session.add(e)
    db_session.flush()

    # Create minimal FileMetadata row referencing the event we just created
    fm = FileMetadata(
        EventID=e.EventID,
        FileName='x.jpg',
        FileType='image/jpeg',
        FileSize=100,
    )
    db_session.add(fm)
    db_session.commit()
    db_session.refresh(fm)

    # Access via FileMetadataID and FileID synonym
    mid = getattr(fm, 'FileMetadataID')
    fid = getattr(fm, 'FileID')
    assert mid == fid

    # Ensure synonym attribute exists
    assert hasattr(fm, 'FileID')
