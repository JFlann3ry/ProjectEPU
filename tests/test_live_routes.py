import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.event import Event, FileMetadata
from app.models.user import User


def _extract_live_token(html: str) -> str:
    m = re.search(r'data-live-token="([^"]+)"', html)
    assert m, "live token not found on page"
    return m.group(1)


@pytest.fixture
def published_event(db_session):
    # Create a dedicated user and event for this test to avoid FK coupling.
    user = db_session.query(User).filter(User.Email == "live-routes@example.test").first()
    if not user:
        user = User(
            FirstName="Live",
            LastName="Routes",
            Email="live-routes@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    e = Event(
        UserID=int(getattr(user, "UserID")),
        Name="Live Test Event",
        Code=f"TESTLIVE{uuid.uuid4().hex[:6].upper()}",
        Password="x",
        Published=True,
        TermsChecked=True,
    )
    db_session.add(e)
    db_session.flush()
    db_session.commit()
    return e


def test_live_page_404_unknown(client: TestClient):
    r = client.get("/live/NOPE")
    assert r.status_code == 404


def test_live_page_published_200(client: TestClient, db_session, published_event):
    r = client.get(f"/live/{published_event.Code}")
    assert r.status_code == 200
    # Basic smoke: ensure template context appears
    assert "Live Slideshow" in r.text


def test_live_data_basic_and_since_and_limit(client: TestClient, db_session, published_event):
    page = client.get(f"/live/{published_event.Code}")
    assert page.status_code == 200
    token = _extract_live_token(page.text)

    # Seed a few FileMetadata rows
    files = []
    for i, name in enumerate(["a.jpg", "b.jpg", "c.mp4", "d.jpg"], start=1):
        fm = FileMetadata(
            EventID=published_event.EventID,
            FileName=name,
            FileType="video/mp4" if name.endswith(".mp4") else "image/jpeg",
            FileSize=1234,
            Deleted=False,
        )
        db_session.add(fm)
        db_session.flush()
        files.append(fm)
    # Add a deleted row to ensure it doesn't appear
    delrow = FileMetadata(
        EventID=published_event.EventID,
        FileName="z.jpg",
        FileType="image/jpeg",
        FileSize=1234,
        Deleted=True,
    )
    db_session.add(delrow)
    db_session.flush()
    db_session.commit()

    # Full fetch
    r = client.get(f"/live/{published_event.Code}/data", params={"token": token})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    got = data.get("files") or []
    # Should include 4 non-deleted items, ordered by id asc
    assert len(got) == 4
    assert got[0]["type"] == "image" and got[0]["src"].split("?")[0].endswith("a.jpg")
    assert got[2]["type"] == "video" and got[2]["src"].split("?")[0].endswith("c.mp4")
    max_id = data.get("max_id")
    assert isinstance(max_id, int)

    # Since filter: get items strictly greater than the first id
    first_id = files[0].FileMetadataID
    r2 = client.get(
        f"/live/{published_event.Code}/data",
        params={"token": token, "since": first_id},
    )
    assert r2.status_code == 200
    data2 = r2.json()
    got2 = data2.get("files") or []
    assert len(got2) == 3
    assert got2[0]["src"].split("?")[0].endswith("b.jpg")

    # Limit cap: request limit=2
    r3 = client.get(
        f"/live/{published_event.Code}/data",
        params={"token": token, "limit": 2},
    )
    assert r3.status_code == 200
    data3 = r3.json()
    got3 = data3.get("files") or []
    assert len(got3) == 2


def test_live_slideshow_script_has_sse_fallback_contract():
    js = Path("static/js/pages/live_slideshow.js").read_text(encoding="utf-8")
    assert "EventSource" in js
    assert "/stream" in js
    assert "function startRealtime()" in js
    assert "pollFailures" in js


def test_live_slideshow_no_inline_config(client: TestClient, db_session, published_event):
    r = client.get(f"/live/{published_event.Code}")
    assert r.status_code == 200
    assert "window.EPU.liveCfg" not in r.text
    assert "EPU.liveCfg" not in r.text


def test_live_data_denies_missing_or_invalid_token(client: TestClient, db_session, published_event):
    r_missing = client.get(f"/live/{published_event.Code}/data")
    assert r_missing.status_code == 403
    assert r_missing.json().get("error") == "forbidden"

    r_bad = client.get(
        f"/live/{published_event.Code}/data",
        params={"token": "bad-token"},
    )
    assert r_bad.status_code == 403
    assert r_bad.json().get("error") == "forbidden"
