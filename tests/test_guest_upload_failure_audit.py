import logging
import re

from fastapi.testclient import TestClient

from app.models.event import Event, FileMetadata, GuestSession
from app.models.user import User


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]*)"', html)
    assert m, "csrf_token input not found"
    return m.group(1)


def _seed_guest_file(db_session):
    user = db_session.query(User).filter(User.Email == "guest-audit@example.test").first()
    if not user:
        user = User(
            FirstName="Guest",
            LastName="Audit",
            Email="guest-audit@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    event = Event(
        UserID=user.UserID,
        Name="Guest Audit Test",
        Code="GATEST",
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
        FileName="guest-audit-test.jpg",
        FileType="image/jpeg",
        FileSize=1024,
        Deleted=False,
    )
    db_session.add(file_rec)
    db_session.flush()
    db_session.commit()

    return event, guest, file_rec


def test_guest_delete_denied_no_cookie_audit(db_session, client: TestClient, caplog):
    event, guest, file_rec = _seed_guest_file(db_session)
    page = client.get(f"/guest/upload/{event.Code}")
    assert page.status_code == 200
    csrf = _extract_csrf(page.text)

    with caplog.at_level(logging.WARNING, logger="audit"):
        r = client.post(
            f"/guest/upload/{event.Code}/delete",
            data={"file_id": str(file_rec.FileMetadataID), "csrf_token": csrf},
        )

    assert r.status_code == 403
    audit_records = [rec for rec in caplog.records if rec.message == "guest.upload.delete.denied"]
    assert len(audit_records) == 1
    assert audit_records[0].__dict__.get("reason") == "not_authorized"


def test_guest_delete_denied_invalid_csrf_audit(db_session, client: TestClient, caplog):
    event, guest, file_rec = _seed_guest_file(db_session)
    client.cookies.set(f"guest_session_{event.Code}", str(guest.GuestID))

    with caplog.at_level(logging.WARNING, logger="audit"):
        r = client.post(
            f"/guest/upload/{event.Code}/delete",
            data={"file_id": str(file_rec.FileMetadataID), "csrf_token": "bad-token"},
        )

    assert r.status_code == 403
    audit_records = [rec for rec in caplog.records if rec.message == "guest.upload.delete.denied"]
    assert len(audit_records) == 1
    assert audit_records[0].__dict__.get("reason") == "csrf_validation_failed"


def test_guest_delete_denied_file_not_found_audit(db_session, client: TestClient, caplog):
    event, guest, file_rec = _seed_guest_file(db_session)

    # Set cookie first, then get CSRF to ensure token validity for session
    client.cookies.set(f"guest_session_{event.Code}", str(guest.GuestID))
    page = client.get(f"/guest/upload/{event.Code}")
    assert page.status_code == 200
    csrf = _extract_csrf(page.text)

    with caplog.at_level(logging.WARNING, logger="audit"):
        r = client.post(
            f"/guest/upload/{event.Code}/delete",
            data={"file_id": "99999", "csrf_token": csrf},
        )

    assert r.status_code == 404
    audit_records = [rec for rec in caplog.records if rec.message == "guest.upload.delete.denied"]
    assert len(audit_records) == 1
    assert audit_records[0].__dict__.get("reason") == "file_not_found"


def test_guest_restore_denied_file_not_found_audit(db_session, client: TestClient, caplog):
    event, guest, file_rec = _seed_guest_file(db_session)

    # Set cookie first, then get CSRF to ensure token validity for session
    client.cookies.set(f"guest_session_{event.Code}", str(guest.GuestID))
    page = client.get(f"/guest/upload/{event.Code}")
    assert page.status_code == 200
    csrf = _extract_csrf(page.text)

    with caplog.at_level(logging.WARNING, logger="audit"):
        r = client.post(
            f"/guest/upload/{event.Code}/restore",
            data={"file_id": "99999", "csrf_token": csrf},
        )

    assert r.status_code == 404
    audit_records = [rec for rec in caplog.records if rec.message == "guest.upload.restore.denied"]
    assert len(audit_records) == 1
    assert audit_records[0].__dict__.get("reason") == "file_not_found_or_not_deleted"


def test_guest_list_denied_no_cookie_audit(db_session, client: TestClient, caplog):
    event, guest, file_rec = _seed_guest_file(db_session)

    with caplog.at_level(logging.WARNING, logger="audit"):
        r = client.get(f"/guest/upload/{event.Code}/list")

    assert r.status_code == 403
    audit_records = [rec for rec in caplog.records if rec.message == "guest.upload.list.denied"]
    assert len(audit_records) == 1
    assert audit_records[0].__dict__.get("reason") == "not_authorized"
