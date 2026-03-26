import uuid
from datetime import datetime, timedelta, timezone

from app.jobs.maintenance import cleanup_stale_guest_sessions
from app.models.event import Event, FileMetadata, GuestMessage, GuestSession
from app.models.user import User


def _seed_owner_and_event(db_session):
    user = db_session.query(User).filter(User.Email == "cleanup-owner@example.test").first()
    if not user:
        user = User(
            FirstName="Cleanup",
            LastName="Owner",
            Email="cleanup-owner@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    event = Event(
        UserID=user.UserID,
        Name="Cleanup Event",
        Code=f"CLN{uuid.uuid4().hex[:8].upper()}",
        Password="pw",
        TermsChecked=True,
        Published=True,
    )
    db_session.add(event)
    db_session.flush()
    return event


def test_guestsession_cleanup_deletes_only_old_unreferenced_rows(db_session):
    now_utc = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)
    old = now_utc - timedelta(days=45)
    fresh = now_utc - timedelta(days=2)

    event = _seed_owner_and_event(db_session)

    stale = GuestSession(EventID=event.EventID, DeviceType="Desktop", CreatedAt=old)
    old_with_file = GuestSession(EventID=event.EventID, DeviceType="Desktop", CreatedAt=old)
    old_with_message = GuestSession(EventID=event.EventID, DeviceType="Desktop", CreatedAt=old)
    fresh_stale = GuestSession(EventID=event.EventID, DeviceType="Desktop", CreatedAt=fresh)
    db_session.add_all([stale, old_with_file, old_with_message, fresh_stale])
    db_session.flush()
    stale_id = int(stale.GuestID)
    old_with_file_id = int(old_with_file.GuestID)
    old_with_message_id = int(old_with_message.GuestID)

    db_session.add(
        FileMetadata(
            EventID=event.EventID,
            GuestID=old_with_file_id,
            FileName="g1.jpg",
            FileType="image/jpeg",
            FileSize=10,
            Deleted=False,
        )
    )
    db_session.add(
        GuestMessage(
            EventID=event.EventID,
            GuestSessionID=old_with_message_id,
            DisplayName="A",
            Message="hello",
        )
    )
    db_session.commit()

    result = cleanup_stale_guest_sessions(
        db_session,
        retention_days=30,
        batch_size=1,
        now_utc=now_utc,
    )

    assert int(result["deleted_rows"]) >= 1

    remaining_ids = {int(x.GuestID) for x in db_session.query(GuestSession).all()}
    assert stale_id not in remaining_ids
