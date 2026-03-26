"""Controlled media serving endpoint.

Replaces the raw /storage StaticFiles mount with an auth-checked endpoint.

Access is granted when **any** of the following hold:
  - Owner: valid ``session_id`` cookie whose UserID matches ``user_id`` and who
    owns ``event_id``.
  - Guest with cookie: a ``guest_session_{event.Code}`` cookie whose GuestID
    maps to a GuestSession row for the requested event (event must be Published).
  - Live/code access: ``?code={event_code}`` query param matches the event's
    Code and the event is Published.  Used by the live slideshow which has no
    login requirement.
"""

import logging
import mimetypes
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.event import Event, GuestSession
from app.services.auth import get_session
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")

# Anchored at module-import time; stable for the lifetime of the process.
_STORAGE_ROOT: Path = Path(os.path.abspath("storage"))


def _safe_local_path(user_id: int, event_id: int, filename: str) -> Path:
    """Return the resolved local Path, or raise 400 on path-traversal attempts."""
    # Reject traversal characters before any filesystem resolution
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="invalid_path")
    candidate = Path("storage") / str(user_id) / str(event_id) / filename
    try:
        resolved = Path(os.path.abspath(str(candidate)))
        resolved.relative_to(_STORAGE_ROOT)  # raises ValueError if outside storage/
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_path")
    return resolved


@router.get("/media/{user_id}/{event_id}/{filename}")
async def serve_media(
    request: Request,
    user_id: int,
    event_id: int,
    filename: str,
    code: str | None = Query(None, max_length=64),
    db: Session = Depends(get_db),
):
    """Serve a stored media file after verifying the requester is authorised."""
    resolved = _safe_local_path(user_id, event_id, filename)

    authorized = False

    # ── 1. Owner check ────────────────────────────────────────────────────────
    # A valid session whose UserID equals the path user_id, and who owns the event.
    sid = request.cookies.get("session_id")
    if sid:
        session_obj = get_session(db=db, session_id=sid)
        if session_obj is not None:
            try:
                req_uid = int(getattr(session_obj, "UserID", -1) or -1)
                if req_uid == user_id:
                    owned = (
                        db.query(Event.EventID)
                        .filter(Event.EventID == event_id, Event.UserID == user_id)
                        .first()
                    )
                    if owned is not None:
                        authorized = True
            except Exception:
                pass

    # ── 2. Published-event access (guest cookie or ?code=) ────────────────────
    if not authorized:
        event = (
            db.query(Event)
            .filter(
                Event.EventID == event_id,
                Event.UserID == user_id,
                Event.Published == True,  # noqa: E712
            )
            .first()
        )
        if event is not None:
            event_code = str(getattr(event, "Code", "") or "")

            # 2a. Guest-session cookie for this event
            guest_cookie = request.cookies.get(f"guest_session_{event_code}")
            if guest_cookie:
                try:
                    gid = int(guest_cookie)
                    gs = (
                        db.query(GuestSession)
                        .filter(
                            GuestSession.GuestID == gid,
                            GuestSession.EventID == event_id,
                        )
                        .first()
                    )
                    if gs is not None:
                        authorized = True
                except Exception:
                    pass

            # 2b. Explicit event code query param (live slideshow, no cookie)
            if not authorized and code and event_code and code == event_code:
                authorized = True

    if not authorized:
        audit.warning(
            "media.access.denied",
            extra={
                "user_id": user_id,
                "event_id": event_id,
                "media_filename": filename,
                "request_id": getattr(request.state, "request_id", None),
                "client": request.client.host if request.client else None,
            },
        )
        raise HTTPException(status_code=403, detail="forbidden")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="not_found")

    mt, _ = mimetypes.guess_type(filename)
    headers = {"Cache-Control": "private, max-age=3600"}
    return FileResponse(str(resolved), media_type=mt or "application/octet-stream", headers=headers)
