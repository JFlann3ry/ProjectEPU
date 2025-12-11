import pytest
from fastapi.testclient import TestClient

from app.models.event import Event, FileMetadata


@pytest.fixture
def published_event(db_session):
    # Ensure a user exists via autouse fixture; create a published event
    e = Event(
        UserID=1,
        Name="Live Test Event",
        Code="TESTLIVE",
        Password="x",
        Published=True,
        TermsChecked=True,
    )
    db_session.add(e)
    db_session.flush()
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

    # Full fetch
    r = client.get(f"/live/{published_event.Code}/data")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    got = data.get("files") or []
    # Should include 4 non-deleted items, ordered by id asc
    assert len(got) == 4
    assert got[0]["type"] == "image" and got[0]["src"].endswith("a.jpg")
    assert got[2]["type"] == "video" and got[2]["src"].endswith("c.mp4")
    max_id = data.get("max_id")
    assert isinstance(max_id, int)

    # Since filter: get items strictly greater than the first id
    first_id = files[0].FileMetadataID
    r2 = client.get(f"/live/{published_event.Code}/data?since={first_id}")
    assert r2.status_code == 200
    data2 = r2.json()
    got2 = data2.get("files") or []
    assert len(got2) == 3
    assert got2[0]["src"].endswith("b.jpg")

    # Limit cap: request limit=2
    r3 = client.get(f"/live/{published_event.Code}/data?limit=2")
    assert r3.status_code == 200
    data3 = r3.json()
    got3 = data3.get("files") or []
    assert len(got3) == 2
