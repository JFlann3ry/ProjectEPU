import io
import re

from app.models.event import Event, FileMetadata
from app.models.user import User
from app.services.auth import create_session


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]*)"', html)
    assert m, "csrf_token input not found"
    return m.group(1)


def _jpeg_bytes(size: int = 2048) -> bytes:
    return b"\xff\xd8\xff\xdb" + (b"0" * size) + b"\xff\xd9"


def _login_owner(db_session, client, user):
    sess = create_session(db_session, user_id=int(getattr(user, "UserID")))
    client.cookies.set("session_id", str(sess.SessionID))


def _make_owner_event(db_session):
    user = db_session.query(User).filter(User.Email == "owner-limit@example.test").first()
    if not user:
        user = User(
            FirstName="Owner",
            LastName="Limit",
            Email="owner-limit@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()
    event = Event(
        UserID=user.UserID,
        Name="Owner Limit Event",
        Code="OWNLIM",
        Password="pw",
        TermsChecked=True,
        Published=True,
    )
    db_session.add(event)
    db_session.flush()
    return user, event


def _make_guest_event(db_session):
    user = db_session.query(User).filter(User.Email == "guest-limit@example.test").first()
    if not user:
        user = User(
            FirstName="Guest",
            LastName="Limit",
            Email="guest-limit@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()
    event = Event(
        UserID=user.UserID,
        Name="Guest Limit Event",
        Code="GSTLIM",
        Password="pw",
        TermsChecked=True,
        Published=True,
    )
    db_session.add(event)
    db_session.flush()
    return event


def test_owner_upload_rejects_large_file_early(db_session, client, monkeypatch):
    import app.core.settings as core_settings

    user, event = _make_owner_event(db_session)
    _login_owner(db_session, client, user)
    monkeypatch.setattr(core_settings.settings, "MAX_UPLOAD_BYTES", 128, raising=False)

    before = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    r = client.post(
        f"/events/{event.EventID}/upload",
        files={"files": ("big.jpg", io.BytesIO(_jpeg_bytes(1024)), "image/jpeg")},
    )

    assert r.status_code in (200, 303)
    after = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    assert after == before


def test_guest_upload_rejects_large_file_early(db_session, client, monkeypatch):
    import app.core.settings as core_settings

    event = _make_guest_event(db_session)
    monkeypatch.setattr(core_settings.settings, "MAX_UPLOAD_BYTES", 128, raising=False)

    page = client.get(f"/guest/upload/{event.Code}")
    assert page.status_code == 200
    csrf = _extract_csrf(page.text)

    before = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    r = client.post(
        f"/guest/upload/{event.Code}",
        data={"csrf_token": csrf},
        files={"files": ("big.jpg", io.BytesIO(_jpeg_bytes(1024)), "image/jpeg")},
    )

    assert r.status_code in (200, 303)
    after = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    assert after == before
