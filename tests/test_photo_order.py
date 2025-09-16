from datetime import datetime, timedelta, timezone

from app.models.event import Event, FileMetadata
from app.models.photo_order import EventGalleryOrder
from app.services.photo_order_service import (
    rebuild_event_gallery_order,
)


def make_dt(offset_seconds: int):
    return datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)


def test_rebuild_event_gallery_order_basic(db_session):
    # Create event using an existing test user to satisfy FK constraints
    from app.models.user import User

    user = db_session.query(User).first()
    assert user is not None
    ev = Event(Name="T1", Code="c1", Password="p", UserID=user.UserID)
    db_session.add(ev)
    db_session.flush()

    # Create files: two with captured times, one without (should sort last)
    f1 = FileMetadata(
        EventID=ev.EventID,
        FileName="a.jpg",
        FileType="image/jpeg",
        FileSize=100,
        CapturedDateTime=make_dt(-30),
        UploadDate=make_dt(-20),
    )
    f2 = FileMetadata(
        EventID=ev.EventID,
        FileName="b.jpg",
        FileType="image/jpeg",
        FileSize=100,
        CapturedDateTime=make_dt(-10),
        UploadDate=make_dt(-5),
    )
    f3 = FileMetadata(
        EventID=ev.EventID,
        FileName="c.jpg",
        FileType="image/jpeg",
        FileSize=100,
        CapturedDateTime=None,
        UploadDate=make_dt(-1),
    )
    db_session.add_all([f1, f2, f3])
    db_session.flush()

    # Ensure the EventGalleryOrder table exists in the test DB (some test setups use a fresh DB)
    from app.models.photo_order import EventGalleryOrder as _EGO

    _EGO.__table__.create(bind=db_session.get_bind(), checkfirst=True)

    created = rebuild_event_gallery_order(db_session, ev.EventID)

    # Expect 3 created
    assert len(created) == 3

    # Get stable ids for the files (inspect.identity works regardless of aliasing)
    from sqlalchemy import inspect

    f1_id = inspect(f1).identity[0]
    f2_id = inspect(f2).identity[0]
    f3_id = inspect(f3).identity[0]

    # Query back and assert ordinals
    rows = (
        db_session.query(EventGalleryOrder)
        .filter(EventGalleryOrder.EventID == ev.EventID)
        .order_by(EventGalleryOrder.Ordinal)
        .all()
    )
    assert [r.FileMetadataID for r in rows] == [f1_id, f2_id, f3_id]
    assert [r.Ordinal for r in rows] == [1, 2, 3]
