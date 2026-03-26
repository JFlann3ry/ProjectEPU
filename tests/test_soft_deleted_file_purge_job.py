from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.jobs.maintenance import purge_soft_deleted_files
from app.models.event import Event, FileMetadata
from app.models.user import User


def _ensure_user(db_session) -> User:
    user = db_session.query(User).filter(User.Email == "softpurge@example.test").first()
    if not user:
        user = User(
            FirstName="Soft",
            LastName="Purge",
            Email="softpurge@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()
    return user


def _seed_event_and_file(
    db_session,
    *,
    user_id: int,
    code: str,
    file_name: str,
    deleted_at: datetime,
) -> tuple[Event, FileMetadata]:
    event = Event(UserID=user_id, Name=f"Event {code}", Code=code, Password="pw", TermsChecked=True)
    db_session.add(event)
    db_session.flush()

    file_row = FileMetadata(
        EventID=int(event.EventID),
        FileName=file_name,
        FileType="image/jpeg",
        FileSize=10,
        Deleted=True,
        DeletedAt=deleted_at,
    )
    db_session.add(file_row)
    db_session.flush()
    return event, file_row


def test_soft_deleted_file_purge_deletes_old_rows_and_storage(db_session, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    user = _ensure_user(db_session)
    user_id = int(getattr(user, "UserID"))
    now_utc = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)

    old_deleted_at = (now_utc - timedelta(days=45)).replace(tzinfo=None)
    fresh_deleted_at = (now_utc - timedelta(days=5)).replace(tzinfo=None)

    old_event, old_file = _seed_event_and_file(
        db_session,
        user_id=user_id,
        code="SDPOLD",
        file_name="old.jpg",
        deleted_at=old_deleted_at,
    )
    fresh_event, fresh_file = _seed_event_and_file(
        db_session,
        user_id=user_id,
        code="SDPNEW",
        file_name="fresh.jpg",
        deleted_at=fresh_deleted_at,
    )
    db_session.commit()

    old_path = Path("storage") / str(user_id) / str(int(old_event.EventID)) / str(old_file.FileName)
    old_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.write_bytes(b"old")

    old_thumb = (
        Path("storage")
        / str(user_id)
        / str(int(old_event.EventID))
        / "thumbnails"
        / f"{int(old_file.FileMetadataID)}_480.jpg"
    )
    old_thumb.parent.mkdir(parents=True, exist_ok=True)
    old_thumb.write_bytes(b"thumb")

    fresh_path = (
        Path("storage") / str(user_id) / str(int(fresh_event.EventID)) / str(fresh_file.FileName)
    )
    fresh_path.parent.mkdir(parents=True, exist_ok=True)
    fresh_path.write_bytes(b"fresh")

    calls: list[dict] = []

    def _fake_record(*_args, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.jobs.maintenance._record_job_run_log", _fake_record)

    result = purge_soft_deleted_files(
        db_session,
        retention_days=30,
        batch_size=10,
        now_utc=now_utc,
    )

    assert result["deleted_rows"] == 1
    assert result["deleted_files"] == 1
    assert result["batches"] == 1
    assert not old_path.exists()
    assert not old_thumb.exists()
    assert fresh_path.exists()

    old_left = (
        db_session.query(FileMetadata)
        .filter(FileMetadata.FileMetadataID == int(old_file.FileMetadataID))
        .count()
    )
    fresh_left = (
        db_session.query(FileMetadata)
        .filter(FileMetadata.FileMetadataID == int(fresh_file.FileMetadataID))
        .count()
    )
    assert old_left == 0
    assert fresh_left == 1

    assert calls
    assert calls[-1]["job_name"] == "EPU_SoftDeletedFile_Purge"
    assert calls[-1]["succeeded"] is True
