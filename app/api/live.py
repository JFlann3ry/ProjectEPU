"""Live Gallery Slideshow endpoints (public, event-code based).

This provides a dedicated, minimal UI for full-screen slideshows that auto-advance
and pick up new uploads as they arrive. Guests can open it using the event's code.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from fastapi import APIRouter, Depends, Path, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.models.event import Event, FileMetadata
from app.services.rate_limit import allow as rate_allow
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


def _shape_live_items(
    rows, user_id: int, event_id: int
) -> list[dict]:
    items: list[dict] = []
    for fid, ftype, fname in rows or []:
        try:
            t = (ftype or "").lower()
            if t.startswith("image"):
                # Serve the original image from storage for maximum quality
                base = f"/storage/{int(user_id)}/{int(event_id)}/{fname}"
                items.append(
                    {
                        "id": int(fid),
                        "type": "image",
                        "src": base,
                    }
                )
            elif t.startswith("video"):
                base = f"/storage/{int(user_id)}/{int(event_id)}/{fname}"
                items.append(
                    {
                        "id": int(fid),
                        "type": "video",
                        "src": base,
                    }
                )
            else:
                # Skip unsupported types for the slideshow
                continue
        except Exception:
            continue
    return items


@router.get("/live/{event_code}", response_class=HTMLResponse)
async def live_slideshow_page(
    request: Request,
    event_code: str = Path(..., min_length=1, max_length=32),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.Code == event_code).first()
    if not event or not getattr(event, "Published", False):
        # Keep a friendly 403 for unpublished/unknown to avoid leaking codes
        return templates.TemplateResponse(
            request,
            "404.html",
            status_code=404,
        )
    audit.info(
        "live.slideshow.page",
        extra={
            "event_id": getattr(event, "EventID", None),
            "event_code": event_code,
            "client": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return templates.TemplateResponse(
        request,
        "live_slideshow.html",
        context={
            "event_code": event_code,
            "event_name": getattr(event, "Name", ""),
        },
    )


@router.get("/live/{event_code}/data", response_class=JSONResponse)
async def live_slideshow_data(
    request: Request,
    event_code: str,
    since: int | None = Query(None, ge=0, description="Return items with FileID greater than this value"),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    # Basic rate limiting (e.g., 60 requests / 60s per IP+event)
    try:
        client_ip = request.client.host if request.client else "anon"
        rl_key = f"live:data:{event_code}:{client_ip}"
        if not rate_allow(rl_key, limit=60, window_seconds=60):
            raise HTTPException(status_code=429, detail="rate_limited")
    except HTTPException:
        raise
    except Exception:
        # If limiter fails, continue without blocking
        pass
    event = db.query(Event).filter(Event.Code == event_code).first()
    if not event or not getattr(event, "Published", False):
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    eid = int(getattr(event, "EventID"))
    uid = int(getattr(event, "UserID"))

    q = (
        db.query(FileMetadata.FileMetadataID, FileMetadata.FileType, FileMetadata.FileName)
        .filter(FileMetadata.EventID == eid, ~FileMetadata.Deleted)
    )
    if since is not None:
        q = q.filter(FileMetadata.FileMetadataID > int(since))
    # Order chronologically by primary key as a proxy for upload time
    rows = q.order_by(FileMetadata.FileMetadataID.asc()).limit(limit).all()

    items = _shape_live_items(rows, user_id=uid, event_id=eid)
    max_id = None
    try:
        if rows:
            max_id = int(rows[-1][0])
    except Exception:
        max_id = None

    return JSONResponse({"ok": True, "files": items, "max_id": max_id})
