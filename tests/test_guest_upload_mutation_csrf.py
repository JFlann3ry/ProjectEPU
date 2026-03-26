import re

from fastapi.testclient import TestClient

from app.models.event import Event, FileMetadata, GuestSession
from app.models.user import User


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]*)"', html)
    assert m, "csrf_token input not found"
    return m.group(1)


def _seed_guest_file(db_session):
    user = db_session.query(User).filter(User.Email == "guest-mutation-csrf@example.test").first()
    if not user:
        user = User(
            FirstName="Guest",
            LastName="Mutation",
            Email="guest-mutation-csrf@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    event = Event(
        UserID=user.UserID,
        Name="Guest Mutation CSRF",
        Code="GMCSRF",
        Password="pw",
        TermsChecked=True,
        Published=True,
    )
    db_session.add(event)
    db_session.flush()

    guest = GuestSession(
        EventID=event.EventID,
        DeviceType="Desktop",
        GuestEmail="guest@example.test",
        TermsChecked=True,
    )
    db_session.add(guest)
    db_session.flush()

    file_rec = FileMetadata(
        EventID=event.EventID,
        GuestID=guest.GuestID,
        FileName="guest-delete-test.jpg",
        FileType="image/jpeg",
        FileSize=1024,
        Deleted=False,
    )
    db_session.add(file_rec)
    db_session.flush()
    db_session.commit()

    return event, guest, file_rec


def test_guest_delete_requires_valid_csrf(db_session, client: TestClient):
    event, guest, file_rec = _seed_guest_file(db_session)
    client.cookies.set(f"guest_session_{event.Code}", str(guest.GuestID))

    page = client.get(f"/guest/upload/{event.Code}")
    assert page.status_code == 200
    csrf = _extract_csrf(page.text)

    bad = client.post(
        f"/guest/upload/{event.Code}/delete",
        data={"file_id": str(file_rec.FileMetadataID), "csrf_token": "bad-token"},
    )
    assert bad.status_code == 403

    ok = client.post(
        f"/guest/upload/{event.Code}/delete",
        data={"file_id": str(file_rec.FileMetadataID), "csrf_token": csrf},
    )
    assert ok.status_code == 200

    refreshed = (
        db_session.query(FileMetadata)
        .filter(FileMetadata.FileMetadataID == file_rec.FileMetadataID)
        .first()
    )
    assert refreshed is not None
    assert bool(getattr(refreshed, "Deleted", False)) is True
