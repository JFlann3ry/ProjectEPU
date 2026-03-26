import logging
from datetime import timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.models.event import Event
from app.services.auth import require_user
from app.services.email_utils import send_event_date_locked_email
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.post("/events/{event_id}/lock-date", response_class=HTMLResponse)
async def lock_event_date(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if not event:
        return RedirectResponse("/events", status_code=303)
    # Basic ownership check
    try:
        _uid = getattr(user, "UserID", None)
        if _uid is not None and getattr(event, "UserID", None) not in (None, _uid):
            return RedirectResponse(f"/events/{event_id}", status_code=303)
    except Exception:
        pass
    # Only lock if a date exists and not already locked
    if getattr(event, "Date", None) and not getattr(event, "IsDateLocked", False):
        # Back-compat: mark Published true as well
        try:
            setattr(event, "Published", True)
        except Exception:
            pass
        # New fields if present
        try:
            setattr(event, "IsDateLocked", True)
        except Exception:
            pass
        try:
            from datetime import datetime as _dt

            setattr(event, "DateLockedAt", _dt.now(timezone.utc))
        except Exception:
            pass
        # Insert EventLockAudit row
        try:
            from app.models.event import EventLockAudit

            db.add(
                EventLockAudit(
                    EventID=event.EventID,
                    UserID=getattr(user, "UserID", None),
                    ClientIP=(request.client.host if request.client else None),
                    UserAgent=request.headers.get("user-agent", None),
                    RequestID=getattr(request.state, "request_id", None),
                    OldDate=getattr(event, "Date", None),
                    NewDate=getattr(event, "Date", None),
                )
            )
        except Exception:
            pass
        db.commit()
        # Send confirmation email (non-blocking best-effort)
        try:
            to_email = None
            try:
                # User dependency is the locker; ensure we have their email.
                to_email = getattr(user, "Email", None)
            except Exception:
                to_email = None
            if to_email:
                # Build a friendly date string and dashboard URL.
                date_str = ""
                try:
                    d = getattr(event, "Date", None)
                    date_str = d.strftime("%d-%m-%Y") if d else ""
                except Exception:
                    pass
                base_url = str(request.base_url).rstrip("/")
                dash_url = f"{base_url}/events/{event.EventID}"
                await send_event_date_locked_email(
                    to_email,
                    getattr(event, "Name", "Your Event"),
                    date_str,
                    dash_url,
                )
        except Exception:
            pass
        audit.info(
            "events.date.locked",
            extra={
                "event_id": event_id,
                "user_id": getattr(user, "UserID", None),
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
    # Prefer code-based redirect when available
    try:
        if getattr(event, "Code", None):
            return RedirectResponse(f"/events/code/{event.Code}", status_code=303)
    except Exception:
        pass
    return RedirectResponse(f"/events/{event_id}", status_code=303)


@router.post("/e/{code}/lock-date", response_class=HTMLResponse)
async def lock_event_date_by_code(
    request: Request,
    code: str,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    ev = db.query(Event).filter(Event.Code == code).first()
    if not ev:
        return RedirectResponse("/events", status_code=303)
    # Delegate to existing numeric handler for business logic
    return await lock_event_date(request, int(getattr(ev, "EventID")), db, user)
