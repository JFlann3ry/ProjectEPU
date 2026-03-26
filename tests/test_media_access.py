"""Tests for the /media/{user_id}/{event_id}/{filename} controlled-access endpoint."""

from fastapi.testclient import TestClient

from app.api.media import _safe_local_path
from app.models.event import Event
from app.models.user import User
from app.services.auth import create_session


def _make_user_event(db_session, email: str, code: str, published: bool = True):
    user = db_session.query(User).filter(User.Email == email).first()
    if not user:
        user = User(
            FirstName="Media",
            LastName="Test",
            Email=email,
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()
    event = Event(
        UserID=user.UserID,
        Name="Media Test Event",
        Code=code,
        Password="",
        TermsChecked=True,
        Published=published,
    )
    db_session.add(event)
    db_session.flush()
    return user, event


def test_media_unauthenticated_returns_403(client: TestClient, db_session):
    """No auth cookies and no code param must produce 403 — never serve raw files."""
    user, event = _make_user_event(db_session, "media-anon@example.test", "MNOANON")
    uid = int(user.UserID)
    eid = int(event.EventID)
    r = client.get(f"/media/{uid}/{eid}/photo.jpg")
    assert r.status_code == 403


def test_media_path_traversal_rejected(client: TestClient):
    """Filename with '..' is rejected by the path validator (HTTP normalizes the URL
    before it reaches the handler, so we test the guard function directly)."""
    import pytest as _pytest
    from fastapi import HTTPException as _HTTPEx

    with _pytest.raises(_HTTPEx) as exc_info:
        _safe_local_path(1, 1, "..")
    assert exc_info.value.status_code == 400

    with _pytest.raises(_HTTPEx) as exc_info2:
        _safe_local_path(1, 1, "a/b")
    assert exc_info2.value.status_code == 400


def test_media_owner_session_authorized_file_not_found(client: TestClient, db_session):
    """Owner with valid session is authorised; if the file doesn't exist, 404 not 403."""
    user, event = _make_user_event(db_session, "media-owner@example.test", "MOWNER")
    uid = int(user.UserID)
    eid = int(event.EventID)
    sess = create_session(db_session, user_id=uid)
    client.cookies.set("session_id", str(sess.SessionID))
    try:
        r = client.get(f"/media/{uid}/{eid}/nonexistent.jpg")
        assert r.status_code == 404
    finally:
        client.cookies.clear()


def test_media_code_param_authorized_file_not_found(client: TestClient, db_session):
    """Valid ?code= for a published event is authorised; absent file → 404."""
    user, event = _make_user_event(db_session, "media-code@example.test", "MCODE1")
    uid = int(user.UserID)
    eid = int(event.EventID)
    r = client.get(f"/media/{uid}/{eid}/nonexistent.jpg?code=MCODE1")
    assert r.status_code == 404


def test_media_wrong_code_returns_403(client: TestClient, db_session):
    """A code that doesn't match the event must not grant access."""
    user, event = _make_user_event(db_session, "media-badcode@example.test", "MBAD01")
    uid = int(user.UserID)
    eid = int(event.EventID)
    r = client.get(f"/media/{uid}/{eid}/photo.jpg?code=WRONGCODE")
    assert r.status_code == 403


def test_media_unpublished_event_code_denied(client: TestClient, db_session):
    """Code-based access on an unpublished event must be denied (403)."""
    user, event = _make_user_event(db_session, "media-unp@example.test", "MUNP01", published=False)
    uid = int(user.UserID)
    eid = int(event.EventID)
    r = client.get(f"/media/{uid}/{eid}/photo.jpg?code=MUNP01")
    assert r.status_code == 403
