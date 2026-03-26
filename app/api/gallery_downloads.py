import io
import os
import zipfile

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.services.auth import require_user
from db import get_db

router = APIRouter()


def _get_user_file_records(db: Session, user_id: int, file_ids: list[int]):
    from app.models.event import Event, FileMetadata

    if not file_ids:
        return []
    # Ensure files belong to user's events
    q = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == user_id, FileMetadata.FileMetadataID.in_(file_ids))
    )
    return q.all()


@router.post("/gallery/download-zip")
async def download_zip(
    request: Request,
    file_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    user_id = user.UserID
    files = _get_user_file_records(db, user_id, file_ids)
    # Enforce plan-based cap for bulk downloads if configured
    try:
        from app.services.billing_utils import get_active_plan

        _plan, features = get_active_plan(db, int(user_id))
        max_zip = int(features.get("max_zip_download_items", 0) or 0)
        if max_zip and len(files) > max_zip:
            files = files[:max_zip]
    except Exception:
        pass
    if not files:
        return RedirectResponse(url=(request.headers.get("referer") or "/gallery"), status_code=303)
    # Build zip in-memory. This is OK for small/medium sets.
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            fname = str(getattr(f, "FileName", ""))
            path = os.path.join("storage", str(user_id), str(f.EventID), fname)
            if os.path.exists(path):
                arcname = os.path.join(str(f.EventID), fname)
                try:
                    zf.write(path, arcname=arcname)
                except Exception:
                    continue
    zip_bytes.seek(0)
    headers = {"Content-Disposition": "attachment; filename=download.zip"}
    return StreamingResponse(zip_bytes, media_type="application/zip", headers=headers)
