from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.gallery_mutations_delete_restore import router as gallery_delete_restore_router
from app.api.gallery_mutations_permadelete import router as gallery_permadelete_router
from app.api.gallery_mutations_shared import DELETION_LOGS
from app.core.settings import settings
from app.models.event import Event, FileMetadata
from app.services.auth import require_admin, require_user
from db import get_db

router = APIRouter()


@router.post("/gallery/actions/delete-debug")
async def gallery_delete_debug(
    file_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Debug-only endpoint for delete matching without mutating data."""
    if not getattr(settings, "DEBUG_ROUTES_ENABLED", False):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        q = (
            db.query(FileMetadata.FileMetadataID)
            .join(Event, Event.EventID == FileMetadata.EventID)
            .filter(Event.UserID == user.UserID, FileMetadata.FileMetadataID.in_(file_ids))
        )
        matched = [r[0] for r in q.all()]
        count_q = (
            db.query(FileMetadata)
            .join(Event, Event.EventID == FileMetadata.EventID)
            .filter(Event.UserID == user.UserID, FileMetadata.FileMetadataID.in_(file_ids))
        )
        est = count_q.count()
        return JSONResponse({"ok": True, "matched": matched, "estimate": est})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/debug/gallery/delete_logs")
def get_delete_logs(admin=Depends(require_admin)):
    """Admin-only: return in-memory recent delete attempts."""
    if not getattr(settings, "DEBUG_ROUTES_ENABLED", False):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        return JSONResponse({"ok": True, "logs": list(DELETION_LOGS)})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


router.include_router(gallery_delete_restore_router)
router.include_router(gallery_permadelete_router)
