import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.event import Event, FileMetadata
from app.services.auth import require_user
from app.services.thumbs import cleanup_thumbnails
from db import get_db

router = APIRouter()


@router.post("/gallery/actions/permadelete")
async def gallery_permanent_delete(
    request: Request,
    file_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Permanently delete selected files (disk + DB) and purge thumbnails."""
    uid = int(getattr(user, "UserID"))
    files = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == uid, FileMetadata.FileMetadataID.in_(file_ids))
        .all()
    )
    base_paths = []
    for f in files:
        eid = int(getattr(f, "EventID"))
        fname = str(getattr(f, "FileName"))
        base_paths.append((eid, fname, int(getattr(f, "FileMetadataID"))))

    for eid, fname, fid in base_paths:
        try:
            path = os.path.join("storage", str(uid), str(eid), fname)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        try:
            cleanup_thumbnails(uid, eid, fid)
        except Exception:
            pass

    try:
        fid_list = [fid for _, _, fid in base_paths]
        db.execute(delete(FileMetadata).where(FileMetadata.FileMetadataID.in_(fid_list)))
        db.commit()
    except Exception:
        db.rollback()

    referer = request.headers.get("referer") or "/gallery"
    return RedirectResponse(url=referer, status_code=303)
