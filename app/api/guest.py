import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.get("/guest/login", response_class=HTMLResponse)
async def guest_login_page(request: Request, code: str | None = None):
    # Prefill event code from deep link (?code=) and signal password autofocus
    if code:
        return templates.TemplateResponse(
            request,
            "guest_log_in.html",
            context={"prefill_code": code, "focus_password": True},
        )
    return templates.TemplateResponse(request, "guest_log_in.html")


@router.post("/guest/login")
async def guest_login(
    request: Request,
    event_code: str = Form(...),
    event_password: str = Form(...),
    db: Session = Depends(get_db),
):
    from app.models.event import Event

    event = db.query(Event).filter(Event.Code == event_code).first()
    if not event:
        audit.warning(
            "guest.login.failed",
            extra={
                "event_code": event_code,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "guest_log_in.html",
            context={"error": "Invalid event code or password."},
        )
    # Simple password check: if event has a password set, require a match
    event_password_value = getattr(event, "Password", "") or ""
    submitted = event_password or ""
    if (event_password_value != "") and (submitted != event_password_value):
        audit.warning(
            "guest.login.failed_password",
            extra={
                "event_id": getattr(event, "EventID", None),
                "event_code": event_code,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "guest_log_in.html",
            context={"error": "Invalid event code or password."},
        )
    audit.info(
        "guest.login.success",
        extra={
            "event_id": getattr(event, "EventID", None),
            "event_code": event_code,
            "client": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    # Do not allow navigation to upload if event is not published yet
    if not getattr(event, "Published", False):
        audit.info(
            "guest.login.unpublished_block",
            extra={
                "event_id": getattr(event, "EventID", None),
                "event_code": event_code,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "guest_log_in.html",
            context={"error": "This event is not available yet."},
        )
    # Redirect straight to the upload page for this event
    return RedirectResponse(url=f"/guest/upload/{event.Code}", status_code=303)
