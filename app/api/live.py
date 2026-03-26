"""Live Gallery Slideshow endpoints (public, event-code based).

This provides a dedicated, minimal UI for full-screen slideshows that auto-advance
and pick up new uploads as they arrive. Guests can open it using the event's code.
"""

from __future__ import annotations

import hmac
import logging
from hashlib import sha256
from time import time

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.event import Event, FileMetadata
from app.services.rate_limit import allow as rate_allow
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


def _issue_live_token(*, event_code: str, event_id: int, ttl_seconds: int = 900) -> str:
    ts = int(time())
    payload = f"{event_code}:{int(event_id)}:{ts}:{int(ttl_seconds)}"
    key = str(getattr(settings, "SECRET_KEY", "") or "change-me").encode("utf-8")
    sig = hmac.new(key, payload.encode("utf-8"), sha256).hexdigest()
    return f"{payload}:{sig}"


def _verify_live_token(token: str, *, event_code: str, event_id: int) -> bool:
    try:
        raw_code, raw_eid, raw_ts, raw_ttl, sig = str(token or "").split(":", 4)
        if raw_code != str(event_code):
            return False
        if int(raw_eid) != int(event_id):
            return False
        ts = int(raw_ts)
        ttl = int(raw_ttl)
        if ttl < 1 or ttl > 86400:
            return False
        now_ts = int(time())
        if now_ts > ts + ttl:
            return False

        payload = f"{raw_code}:{raw_eid}:{raw_ts}:{raw_ttl}"
        key = str(getattr(settings, "SECRET_KEY", "") or "change-me").encode("utf-8")
        expected = hmac.new(key, payload.encode("utf-8"), sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


def _shape_live_items(rows, user_id: int, event_id: int, event_code: str = "") -> list[dict]:
    items: list[dict] = []
    for fid, ftype, fname in rows or []:
        try:
            t = (ftype or "").lower()
            if t.startswith("image"):
                # Serve via auth-gated endpoint; code grants access to live viewers
                base = f"/media/{int(user_id)}/{int(event_id)}/{fname}?code={event_code}"
                items.append(
                    {
                        "id": int(fid),
                        "type": "image",
                        "src": base,
                    }
                )
            elif t.startswith("video"):
                base = f"/media/{int(user_id)}/{int(event_id)}/{fname}?code={event_code}"
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
        except Exception as exc:
            audit.warning(
                "live.slideshow.shape_row_failed",
                extra={
                    "event_id": event_id,
                    "user_id": user_id,
                    "file_id": (fid if "fid" in locals() else None),
                    "file_type": (ftype if "ftype" in locals() else None),
                    "file_name": (fname if "fname" in locals() else None),
                    "error": str(exc),
                },
            )
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
            "live_data_token": _issue_live_token(
                event_code=event_code,
                event_id=int(getattr(event, "EventID", 0)),
                ttl_seconds=900,
            ),
        },
    )


@router.get("/live/{event_code}/data", response_class=JSONResponse)
async def live_slideshow_data(
    request: Request,
    event_code: str,
    token: str | None = Query(None, min_length=1, max_length=256),
    since: int | None = Query(
        None,
        ge=0,
        description="Return items with FileID greater than this value",
    ),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    # Basic rate limiting (e.g., 60 requests / 60s per IP+event)
    try:
        client_ip = request.client.host if request.client else "anon"
        rl_key = f"live:data:{event_code}:{client_ip}"
        if not rate_allow(db, rl_key, limit=60, window_seconds=60):
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

    # Token strategy: live data is available to published events only and requires
    # a short-lived signed token minted by /live/{event_code} page renders.
    if not token or not _verify_live_token(token, event_code=event_code, event_id=eid):
        audit.warning(
            "live.slideshow.data.denied",
            extra={
                "event_id": eid,
                "event_code": event_code,
                "reason": "invalid_or_missing_token",
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)

    q = db.query(FileMetadata.FileMetadataID, FileMetadata.FileType, FileMetadata.FileName).filter(
        FileMetadata.EventID == eid, ~FileMetadata.Deleted
    )
    if since is not None:
        q = q.filter(FileMetadata.FileMetadataID > int(since))
    # Order chronologically by primary key as a proxy for upload time
    rows = q.order_by(FileMetadata.FileMetadataID.asc()).limit(limit).all()

    items = _shape_live_items(rows, user_id=uid, event_id=eid, event_code=event_code)
    max_id = None
    try:
        if rows:
            max_id = int(rows[-1][0])
    except Exception:
        max_id = None

    return JSONResponse({"ok": True, "files": items, "max_id": max_id})
