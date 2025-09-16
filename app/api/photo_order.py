from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.jobs.rebuild_photo_order_job import run_rebuild_for_event
from app.services.auth import require_admin
from db import get_db

router = APIRouter()

@router.post("/events/{event_id}/rebuild-gallery-order")
def rebuild_gallery_order(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Admin-only endpoint to rebuild the EventGalleryOrder for an event.

    Returns: {"created": <n>} on success.
    """
    try:
        created = run_rebuild_for_event(db, event_id)
    except Exception as exc:  # keep broad to surface DB errors
        raise HTTPException(status_code=500, detail=str(exc))
    return {"created": created}
