import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.models.event import Event, FileMetadata

# Keep mutation diagnostics shared across extracted mutation routers.
DELETION_LOGS: list = []
_DELETION_LOG_LIMIT = 200

# Cache DB feature detection for optional columns in mutation flows.
_HAS_DELETED_AT_MUT: Optional[bool] = None


def _has_deleted_at(db: Session) -> bool:
    global _HAS_DELETED_AT_MUT
    if _HAS_DELETED_AT_MUT is not None:
        return _HAS_DELETED_AT_MUT
    try:
        bind = getattr(db, "bind", None)
        if bind is None:
            _HAS_DELETED_AT_MUT = False
            return _HAS_DELETED_AT_MUT
        insp = sa_inspect(bind)
        cols = [c.get("name") for c in insp.get_columns("FileMetadata")]
        _HAS_DELETED_AT_MUT = any((n == "DeletedAt" for n in cols))
    except Exception:
        _HAS_DELETED_AT_MUT = False
    return _HAS_DELETED_AT_MUT


def _get_user_file_records(db: Session, user_id: int, file_ids: list[int]):
    if not file_ids:
        return []
    q = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == user_id, FileMetadata.FileMetadataID.in_(file_ids))
    )
    return q.all()


def append_deletion_log(entry: dict) -> None:
    try:
        DELETION_LOGS.append(entry)
        if len(DELETION_LOGS) > _DELETION_LOG_LIMIT:
            DELETION_LOGS[:] = DELETION_LOGS[-_DELETION_LOG_LIMIT:]
    except Exception:
        # Diagnostic logs should never fail request handling.
        logging.getLogger(__name__).debug("failed to append deletion log", exc_info=True)


def now_utc_naive_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
