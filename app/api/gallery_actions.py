import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.event import Event, FavoriteFile, FileMetadata
from app.services.auth import require_user
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.post("/gallery/favorite")
async def favorite_add(
    file_id: int = Form(...), db: Session = Depends(get_db), user=Depends(require_user)
):
    # Ensure file belongs to user's event
    f = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == user.UserID, FileMetadata.FileMetadataID == file_id)
        .first()
    )
    if not f:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    exists = (
        db.query(FavoriteFile)
        .filter(FavoriteFile.UserID == user.UserID, FavoriteFile.FileMetadataID == file_id)
        .first()
    )
    if not exists:
        db.add(FavoriteFile(UserID=user.UserID, FileMetadataID=file_id))
        db.commit()
    return {"ok": True}


@router.post("/gallery/unfavorite")
async def favorite_remove(
    file_id: int = Form(...), db: Session = Depends(get_db), user=Depends(require_user)
):
    f = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == user.UserID, FileMetadata.FileMetadataID == file_id)
        .first()
    )
    if not f:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    db.query(FavoriteFile).filter(
        FavoriteFile.UserID == user.UserID, FavoriteFile.FileMetadataID == file_id
    ).delete()
    db.commit()
    return {"ok": True}


@router.get("/files/s3/{file_id}/presigned-url")
async def get_s3_presigned_url(
    file_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Generate a presigned S3 URL for a file owned by the user."""
    # Verify file ownership
    f = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == user.UserID, FileMetadata.FileMetadataID == file_id)
        .first()
    )
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if S3 is configured
    s3_service = getattr(__import__("main"), "app", None)
    if not s3_service:
        raise HTTPException(status_code=503, detail="S3 not available")

    s3_service = getattr(s3_service.state, "s3_service", None)
    if not s3_service:
        raise HTTPException(status_code=503, detail="S3 not available")

    try:
        # Build S3 key using the same format as upload
        s3_key = f"uploads/{user.UserID}/{f.EventID}/{file_id}/{f.FileName}"
        presigned_url = s3_service.generate_presigned_url(s3_key, expiration=3600)
        return JSONResponse({"ok": True, "url": presigned_url})
    except Exception as e:
        logging.error(f"Failed to generate presigned URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate URL")
