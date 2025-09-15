from typing import List

import sqlalchemy as sa
from sqlalchemy import delete, inspect
from sqlalchemy.orm import Session

from app.models.event import FileMetadata
from app.models.photo_order import EventGalleryOrder


def rebuild_event_gallery_order(db: Session, event_id: int) -> List[EventGalleryOrder]:
    """Rebuild the EventGalleryOrder for the given event.

    Strategy:
    - Delete existing rows for the event.
    - Query FileMetadata for the event (non-deleted), ordered by CapturedDateTime NULLs last,
      then CapturedDateTime asc, then UploadDate asc.
    - Insert sequential Ordinal starting at 1.
    """
    # Delete existing
    db.execute(delete(EventGalleryOrder).where(EventGalleryOrder.EventID == event_id))
    db.flush()

    # Query files in desired order
    # For compatibility with SQL Server, avoid boolean expressions like `col IS NULL` in ORDER BY.
    # Use a CASE expression to place NULL CapturedDateTime values last when ordering ascending.
    null_case = sa.case((FileMetadata.CapturedDateTime.is_(None), 1), else_=0)
    files = (
        db.query(FileMetadata)
        .filter(FileMetadata.EventID == event_id, ~FileMetadata.Deleted)
        .order_by(null_case, FileMetadata.CapturedDateTime, FileMetadata.UploadDate)
        .all()
    )

    rows = []
    for idx, f in enumerate(files, start=1):
        identity = inspect(f).identity
        if identity and len(identity) >= 1:
            fid = identity[0]
        else:
            # fallback to attribute access
            fid = getattr(f, "FileMetadataID", None) or getattr(f, "FileID", None)
        rows.append({"EventID": event_id, "FileMetadataID": int(fid), "Ordinal": idx})

    if rows:
        db.bulk_insert_mappings(EventGalleryOrder, rows)
    db.commit()
    return rows
