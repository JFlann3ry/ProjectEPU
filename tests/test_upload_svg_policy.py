import io
import re

from fastapi.testclient import TestClient

from app.models.event import Event, FileMetadata
from app.models.user import User
from app.services.auth import create_session
from app.services.mime_utils import is_allowed_mime


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]*)"', html)
    assert m, "csrf_token input not found"
    return m.group(1)


def _svg_bytes() -> bytes:
    return (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        b'<rect width="10" height="10"/></svg>'
    )


def _make_owner_event(db_session):
    user = db_session.query(User).filter(User.Email == "svg-policy-owner@example.test").first()
    if not user:
        user = User(
            FirstName="Svg",
            LastName="Owner",
            Email="svg-policy-owner@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()
    event = Event(
        UserID=user.UserID,
        Name="SVG Policy Event",
        Code="SVGPOL",
        Password="pw",
        TermsChecked=True,
        Published=True,
    )
    db_session.add(event)
    db_session.flush()
    return user, event


def _login_owner(db_session, client: TestClient, user):
    sess = create_session(db_session, user_id=int(getattr(user, "UserID")))
    client.cookies.set("session_id", str(sess.SessionID))


def test_is_allowed_mime_rejects_svg():
    ok, mime = is_allowed_mime(
        _svg_bytes(),
        allowed_prefixes=("image/", "video/"),
        fallback_content_type="image/svg+xml",
    )
    assert ok is False
    assert "svg" in mime.lower()


def test_is_allowed_mime_rejects_svg_spoofed_as_jpeg():
    ok, mime = is_allowed_mime(
        _svg_bytes(),
        allowed_prefixes=("image/", "video/"),
        fallback_content_type="image/jpeg",
    )
    assert ok is False
    assert "svg" in mime.lower()


def test_owner_upload_rejects_svg_file(db_session, client):
    user, event = _make_owner_event(db_session)
    _login_owner(db_session, client, user)

    before = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    r = client.post(
        f"/events/{event.EventID}/upload",
        files={"files": ("bad.svg", io.BytesIO(_svg_bytes()), "image/svg+xml")},
    )

    assert r.status_code in (200, 303)
    after = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    assert after == before


def test_owner_upload_rejects_svg_payload_with_jpg_extension(db_session, client):
    user, event = _make_owner_event(db_session)
    _login_owner(db_session, client, user)

    before = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    r = client.post(
        f"/events/{event.EventID}/upload",
        files={"files": ("looks-like-jpg.jpg", io.BytesIO(_svg_bytes()), "image/jpeg")},
    )

    assert r.status_code in (200, 303)
    after = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    assert after == before


def test_guest_upload_rejects_svg_file(db_session, client):
    _user, event = _make_owner_event(db_session)

    page = client.get(f"/guest/upload/{event.Code}")
    assert page.status_code == 200
    csrf = _extract_csrf(page.text)

    before = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    r = client.post(
        f"/guest/upload/{event.Code}",
        data={"csrf_token": csrf},
        files={"files": ("bad.svg", io.BytesIO(_svg_bytes()), "image/svg+xml")},
    )

    assert r.status_code in (200, 303)
    after = db_session.query(FileMetadata).filter(FileMetadata.EventID == event.EventID).count()
    assert after == before
