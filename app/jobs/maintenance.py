from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.album import AlbumPhoto
from app.models.billing import PaymentLog
from app.models.event import Event, FavoriteFile, FileMetadata, GuestMessage, GuestSession
from app.models.export import UserDataExportJob
from app.models.photo_order import EventGalleryOrder
from app.services.thumbs import cleanup_thumbnails

audit = logging.getLogger("audit")


def _record_job_run_log(
    db: Session,
    *,
    job_name: str,
    step_name: str,
    started_at: datetime,
    finished_at: datetime,
    succeeded: bool,
    details: str,
) -> None:
    """Best-effort write to dbo.JobRunLog when the table exists."""
    try:
        db.execute(
            text(
                """
                INSERT INTO JobRunLog (JobName, StepName, StartedAt, FinishedAt, Succeeded, Details)
                VALUES (:job_name, :step_name, :started_at, :finished_at, :succeeded, :details)
                """
            ),
            {
                "job_name": job_name,
                "step_name": step_name,
                "started_at": started_at,
                "finished_at": finished_at,
                "succeeded": 1 if succeeded else 0,
                "details": details[:4000],
            },
        )
        db.commit()
    except Exception:
        # Logging must never fail the maintenance job.
        try:
            db.rollback()
        except Exception:
            pass


def purge_old_payment_logs(
    db: Session,
    *,
    retention_days: int = 90,
    batch_size: int = 10_000,
    now_utc: datetime | None = None,
) -> dict[str, int | str]:
    """Purge PaymentLog rows older than retention_days in batches."""
    if retention_days < 1:
        raise ValueError("retention_days must be >= 1")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    started_at = (now_utc or datetime.now(timezone.utc)).replace(tzinfo=None)
    cutoff = started_at - timedelta(days=retention_days)
    deleted_rows = 0
    batches = 0

    try:
        while True:
            ids = [
                int(row[0])
                for row in (
                    db.query(PaymentLog.LogID)
                    .filter(PaymentLog.CreatedAt.isnot(None), PaymentLog.CreatedAt < cutoff)
                    .order_by(PaymentLog.LogID.asc())
                    .limit(batch_size)
                    .all()
                )
            ]
            if not ids:
                break

            affected = (
                db.query(PaymentLog)
                .filter(PaymentLog.LogID.in_(ids))
                .delete(synchronize_session=False)
            )
            db.commit()
            deleted_rows += int(affected or 0)
            batches += 1

        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        details = (
            f"cutoff={cutoff.isoformat()} retention_days={retention_days} "
            f"batch_size={batch_size} batches={batches} deleted={deleted_rows}"
        )
        _record_job_run_log(
            db,
            job_name="EPU_PaymentLog_Purge",
            step_name="purge_old_payment_logs",
            started_at=started_at,
            finished_at=finished_at,
            succeeded=True,
            details=details,
        )
        audit.info("jobs.paymentlog.purge.completed", extra={"details": details})
        return {
            "retention_days": retention_days,
            "batch_size": batch_size,
            "batches": batches,
            "deleted_rows": deleted_rows,
            "cutoff": cutoff.isoformat(),
        }
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        details = (
            f"cutoff={cutoff.isoformat()} retention_days={retention_days} "
            f"batch_size={batch_size} batches={batches} deleted={deleted_rows} error={exc}"
        )
        _record_job_run_log(
            db,
            job_name="EPU_PaymentLog_Purge",
            step_name="purge_old_payment_logs",
            started_at=started_at,
            finished_at=finished_at,
            succeeded=False,
            details=details,
        )
        raise


def cleanup_completed_exports(
    db: Session,
    *,
    retention_days: int = 30,
    batch_size: int = 1_000,
    now_utc: datetime | None = None,
) -> dict[str, int | str]:
    """Delete completed export rows and files after expiry/retention in batches."""
    if retention_days < 1:
        raise ValueError("retention_days must be >= 1")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    started_at = (now_utc or datetime.now(timezone.utc)).replace(tzinfo=None)
    cutoff = started_at - timedelta(days=retention_days)
    deleted_rows = 0
    deleted_files = 0
    missing_files = 0
    batches = 0

    try:
        while True:
            rows = (
                db.query(UserDataExportJob.JobID, UserDataExportJob.FilePath)
                .filter(UserDataExportJob.Status == "completed")
                .filter(
                    (
                        UserDataExportJob.ExpiresAt.isnot(None)
                        & (UserDataExportJob.ExpiresAt < started_at)
                    )
                    | (
                        UserDataExportJob.CompletedAt.isnot(None)
                        & (UserDataExportJob.CompletedAt < cutoff)
                    )
                )
                .order_by(UserDataExportJob.JobID.asc())
                .limit(batch_size)
                .all()
            )
            if not rows:
                break

            ids: list[int] = []
            for row in rows:
                try:
                    ids.append(int(row[0]))
                except Exception:
                    continue

                path = row[1]
                try:
                    if path and os.path.exists(path):
                        os.remove(path)
                        deleted_files += 1
                    elif path:
                        missing_files += 1
                except Exception:
                    # File cleanup is best-effort; row cleanup still proceeds.
                    missing_files += 1

            if not ids:
                break

            affected = (
                db.query(UserDataExportJob)
                .filter(UserDataExportJob.JobID.in_(ids))
                .delete(synchronize_session=False)
            )
            db.commit()
            deleted_rows += int(affected or 0)
            batches += 1

        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        details = (
            f"cutoff={cutoff.isoformat()} retention_days={retention_days} "
            f"batch_size={batch_size} batches={batches} deleted_rows={deleted_rows} "
            f"deleted_files={deleted_files} missing_files={missing_files}"
        )
        _record_job_run_log(
            db,
            job_name="EPU_Export_Cleanup",
            step_name="cleanup_completed_exports",
            started_at=started_at,
            finished_at=finished_at,
            succeeded=True,
            details=details,
        )
        audit.info("jobs.export.cleanup.completed", extra={"details": details})
        return {
            "retention_days": retention_days,
            "batch_size": batch_size,
            "batches": batches,
            "deleted_rows": deleted_rows,
            "deleted_files": deleted_files,
            "missing_files": missing_files,
            "cutoff": cutoff.isoformat(),
        }
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        details = (
            f"cutoff={cutoff.isoformat()} retention_days={retention_days} "
            f"batch_size={batch_size} batches={batches} deleted_rows={deleted_rows} "
            f"deleted_files={deleted_files} missing_files={missing_files} error={exc}"
        )
        _record_job_run_log(
            db,
            job_name="EPU_Export_Cleanup",
            step_name="cleanup_completed_exports",
            started_at=started_at,
            finished_at=finished_at,
            succeeded=False,
            details=details,
        )
        raise


def cleanup_stale_guest_sessions(
    db: Session,
    *,
    retention_days: int = 30,
    batch_size: int = 5_000,
    now_utc: datetime | None = None,
) -> dict[str, int | str]:
    """Delete old guest sessions that have no dependent files or messages."""
    if retention_days < 1:
        raise ValueError("retention_days must be >= 1")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    started_at = (now_utc or datetime.now(timezone.utc)).replace(tzinfo=None)
    cutoff = started_at - timedelta(days=retention_days)
    deleted_rows = 0
    batches = 0

    try:
        while True:
            rows = (
                db.query(GuestSession.GuestID)
                .outerjoin(FileMetadata, FileMetadata.GuestID == GuestSession.GuestID)
                .outerjoin(GuestMessage, GuestMessage.GuestSessionID == GuestSession.GuestID)
                .filter(GuestSession.CreatedAt.isnot(None), GuestSession.CreatedAt < cutoff)
                .filter(FileMetadata.FileMetadataID.is_(None))
                .filter(GuestMessage.GuestMessageID.is_(None))
                .distinct()
                .order_by(GuestSession.GuestID.asc())
                .limit(batch_size)
                .all()
            )
            if not rows:
                break

            ids = [int(r[0]) for r in rows]
            affected = (
                db.query(GuestSession)
                .filter(GuestSession.GuestID.in_(ids))
                .delete(synchronize_session=False)
            )
            db.commit()
            deleted_rows += int(affected or 0)
            batches += 1

        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        details = (
            f"cutoff={cutoff.isoformat()} retention_days={retention_days} "
            f"batch_size={batch_size} batches={batches} deleted={deleted_rows}"
        )
        _record_job_run_log(
            db,
            job_name="EPU_GuestSession_Cleanup",
            step_name="cleanup_stale_guest_sessions",
            started_at=started_at,
            finished_at=finished_at,
            succeeded=True,
            details=details,
        )
        audit.info("jobs.guestsession.cleanup.completed", extra={"details": details})
        return {
            "retention_days": retention_days,
            "batch_size": batch_size,
            "batches": batches,
            "deleted_rows": deleted_rows,
            "cutoff": cutoff.isoformat(),
        }
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        details = (
            f"cutoff={cutoff.isoformat()} retention_days={retention_days} "
            f"batch_size={batch_size} batches={batches} deleted={deleted_rows} error={exc}"
        )
        _record_job_run_log(
            db,
            job_name="EPU_GuestSession_Cleanup",
            step_name="cleanup_stale_guest_sessions",
            started_at=started_at,
            finished_at=finished_at,
            succeeded=False,
            details=details,
        )
        raise


def purge_soft_deleted_files(
    db: Session,
    *,
    retention_days: int = 30,
    batch_size: int = 1_000,
    now_utc: datetime | None = None,
) -> dict[str, int | str]:
    """Permanently delete soft-deleted files after retention_days."""
    if retention_days < 1:
        raise ValueError("retention_days must be >= 1")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    started_at = (now_utc or datetime.now(timezone.utc)).replace(tzinfo=None)
    cutoff = started_at - timedelta(days=retention_days)
    deleted_rows = 0
    deleted_files = 0
    missing_files = 0
    batches = 0

    try:
        while True:
            rows = (
                db.query(
                    FileMetadata.FileMetadataID,
                    FileMetadata.EventID,
                    FileMetadata.FileName,
                    Event.UserID,
                )
                .join(Event, Event.EventID == FileMetadata.EventID)
                .filter(
                    FileMetadata.Deleted == True,  # noqa: E712
                    FileMetadata.DeletedAt.isnot(None),
                    FileMetadata.DeletedAt < cutoff,
                )
                .order_by(FileMetadata.FileMetadataID.asc())
                .limit(batch_size)
                .all()
            )
            if not rows:
                break

            file_ids: list[int] = []
            for row in rows:
                try:
                    fid = int(row[0])
                    eid = int(row[1])
                    fname = str(row[2])
                    uid = int(row[3])
                except Exception:
                    continue
                file_ids.append(fid)

                # File cleanup is best-effort; DB cleanup still proceeds.
                try:
                    path = os.path.join("storage", str(uid), str(eid), fname)
                    if os.path.exists(path):
                        os.remove(path)
                        deleted_files += 1
                    else:
                        missing_files += 1
                except Exception:
                    missing_files += 1

                try:
                    cleanup_thumbnails(uid, eid, fid)
                except Exception:
                    pass

            if not file_ids:
                break

            (
                db.query(FavoriteFile)
                .filter(FavoriteFile.FileMetadataID.in_(file_ids))
                .delete(synchronize_session=False)
            )
            (
                db.query(EventGalleryOrder)
                .filter(EventGalleryOrder.FileMetadataID.in_(file_ids))
                .delete(synchronize_session=False)
            )
            (
                db.query(AlbumPhoto)
                .filter(AlbumPhoto.FileID.in_(file_ids))
                .delete(synchronize_session=False)
            )
            affected = (
                db.query(FileMetadata)
                .filter(FileMetadata.FileMetadataID.in_(file_ids))
                .delete(synchronize_session=False)
            )
            db.commit()

            deleted_rows += int(affected or 0)
            batches += 1

        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        details = (
            f"cutoff={cutoff.isoformat()} retention_days={retention_days} "
            f"batch_size={batch_size} batches={batches} deleted_rows={deleted_rows} "
            f"deleted_files={deleted_files} missing_files={missing_files}"
        )
        _record_job_run_log(
            db,
            job_name="EPU_SoftDeletedFile_Purge",
            step_name="purge_soft_deleted_files",
            started_at=started_at,
            finished_at=finished_at,
            succeeded=True,
            details=details,
        )
        audit.info("jobs.softdeleted.purge.completed", extra={"details": details})
        return {
            "retention_days": retention_days,
            "batch_size": batch_size,
            "batches": batches,
            "deleted_rows": deleted_rows,
            "deleted_files": deleted_files,
            "missing_files": missing_files,
            "cutoff": cutoff.isoformat(),
        }
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        details = (
            f"cutoff={cutoff.isoformat()} retention_days={retention_days} "
            f"batch_size={batch_size} batches={batches} deleted_rows={deleted_rows} "
            f"deleted_files={deleted_files} missing_files={missing_files} error={exc}"
        )
        _record_job_run_log(
            db,
            job_name="EPU_SoftDeletedFile_Purge",
            step_name="purge_soft_deleted_files",
            started_at=started_at,
            finished_at=finished_at,
            succeeded=False,
            details=details,
        )
        raise
