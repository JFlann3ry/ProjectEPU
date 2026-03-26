import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.jobs.maintenance import cleanup_completed_exports
from app.models.export import UserDataExportJob
from app.models.user import User


def _mk_file(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"zip-bytes")
    return str(path)


def _ensure_user_id(db_session) -> int:
    user = db_session.query(User).filter(User.Email == "export-cleanup@example.test").first()
    if not user:
        user = User(
            FirstName="Export",
            LastName="Cleanup",
            Email="export-cleanup@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()
    return int(getattr(user, "UserID"))


def _seed_job(
    db_session,
    *,
    user_id: int,
    status: str,
    completed_at: datetime | None,
    expires_at: datetime | None,
    file_path: str | None,
):
    db_session.add(
        UserDataExportJob(
            UserID=user_id,
            Status=status,
            CompletedAt=completed_at,
            ExpiresAt=expires_at,
            FilePath=file_path,
        )
    )


def test_export_cleanup_deletes_expired_completed_rows_and_files(db_session, tmp_path):
    user_id = _ensure_user_id(db_session)
    tag = f"exp{uuid.uuid4().hex[:10]}"
    now_utc = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)
    old = now_utc - timedelta(days=60)
    fresh = now_utc - timedelta(days=2)

    expired_file = _mk_file(tmp_path / "exports" / "u1" / f"{tag}_expired.zip")
    kept_file = _mk_file(tmp_path / "exports" / "u1" / f"{tag}_kept.zip")

    _seed_job(
        db_session,
        user_id=user_id,
        status="completed",
        completed_at=old,
        expires_at=old,
        file_path=expired_file,
    )
    _seed_job(
        db_session,
        user_id=user_id,
        status="completed",
        completed_at=fresh,
        expires_at=now_utc + timedelta(days=1),
        file_path=kept_file,
    )
    _seed_job(
        db_session,
        user_id=user_id,
        status="failed",
        completed_at=old,
        expires_at=old,
        file_path=None,
    )
    db_session.commit()

    result = cleanup_completed_exports(
        db_session,
        retention_days=30,
        batch_size=1,
        now_utc=now_utc,
    )

    assert result["deleted_rows"] == 1
    assert result["deleted_files"] == 1
    assert result["batches"] == 1

    assert not Path(expired_file).exists()
    assert Path(kept_file).exists()

    expired_left = (
        db_session.query(UserDataExportJob)
        .filter(UserDataExportJob.FilePath == expired_file)
        .count()
    )
    assert expired_left == 0


def test_export_cleanup_records_jobrunlog_on_success(db_session, tmp_path, monkeypatch):
    user_id = _ensure_user_id(db_session)
    tag = f"exp{uuid.uuid4().hex[:10]}"
    calls: list[dict] = []

    def _fake_record(*_args, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.jobs.maintenance._record_job_run_log", _fake_record)

    now_utc = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)
    old = now_utc - timedelta(days=60)
    stale_path = _mk_file(tmp_path / "exports" / "u1" / f"{tag}_old.zip")
    _seed_job(
        db_session,
        user_id=user_id,
        status="completed",
        completed_at=old,
        expires_at=old,
        file_path=stale_path,
    )
    db_session.commit()

    cleanup_completed_exports(db_session, retention_days=30, batch_size=10, now_utc=now_utc)

    assert calls
    assert calls[-1]["job_name"] == "EPU_Export_Cleanup"
    assert calls[-1]["succeeded"] is True
