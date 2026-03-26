import logging
import re
import secrets
import string

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.events_edit_submit import router as events_edit_submit_router
from app.api.events_locking import router as events_locking_router
from app.core.templates import templates
from app.models.event import Event, EventCustomisation, EventType, Theme
from app.services.auth import require_user
from app.services.csrf import issue_csrf_token, set_csrf_cookie
from app.services.theme_values import build_theme_view, resolve_effective_theme
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


def _valid_pw(p: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]{6}", str(p or "")))


def _gen_pw(n: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _repair_event_password_if_needed(db: Session, event) -> None:
    try:
        if not event:
            return
        pw = getattr(event, "Password", None) or ""
        if _valid_pw(pw):
            return
        setattr(event, "Password", _gen_pw())
        try:
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    except Exception:
        pass


@router.get("/e/{code}/edit", response_class=HTMLResponse)
async def edit_event_page_code(
    request: Request,
    code: str,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Resolve by short code instead of numeric ID to reduce enumeration risk
    event = db.query(Event).filter(Event.Code == code).first()
    if not event:
        return RedirectResponse("/events", status_code=303)
    # Ownership guard
    try:
        if getattr(event, "UserID", None) != getattr(user, "UserID", None):
            return RedirectResponse("/events", status_code=303)
    except Exception:
        pass
    custom = (
        db.query(EventCustomisation).filter(EventCustomisation.EventID == event.EventID).first()
    )
    themes = db.query(Theme).all()
    selected_theme = None
    try:
        if custom and getattr(custom, "ThemeID", None):
            selected_theme = db.query(Theme).filter(Theme.ThemeID == custom.ThemeID).first()
    except Exception:
        selected_theme = None
    effective_theme = resolve_effective_theme(custom, selected_theme)
    event_types = db.query(EventType).order_by(EventType.Name.asc()).all()
    guest_url = f"/guest/upload/{event.Code}" if event else None
    # Ensure event has a valid 6-char alphanumeric password for display/editing.
    _repair_event_password_if_needed(db, event)
    token = issue_csrf_token(request.cookies.get("session_id"))
    resp = templates.TemplateResponse(
        request,
        "edit_event.html",
        context={
            "event": event,
            "custom": custom,
            "effective_theme": effective_theme,
            "theme_view": build_theme_view(effective_theme),
            "themes": themes,
            "event_types": event_types,
            "guest_url": guest_url,
            "csrf_token": token,
        },
    )
    set_csrf_cookie(resp, token, httponly=True)
    return resp


@router.get("/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_page(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Compatibility: redirect numeric ID URL to code-based path if possible
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if event and getattr(event, "Code", None):
        return RedirectResponse(f"/e/{event.Code}/edit", status_code=307)
    # Fallback to legacy render
    custom = db.query(EventCustomisation).filter(EventCustomisation.EventID == event_id).first()
    themes = db.query(Theme).all()
    selected_theme = None
    try:
        if custom and getattr(custom, "ThemeID", None):
            selected_theme = db.query(Theme).filter(Theme.ThemeID == custom.ThemeID).first()
    except Exception:
        selected_theme = None
    effective_theme = resolve_effective_theme(custom, selected_theme)
    event_types = db.query(EventType).order_by(EventType.Name.asc()).all()
    guest_url = f"/guest/upload/{event.Code}" if event else None
    _repair_event_password_if_needed(db, event)

    return templates.TemplateResponse(
        request,
        "edit_event.html",
        context={
            "event": event,
            "custom": custom,
            "effective_theme": effective_theme,
            "theme_view": build_theme_view(effective_theme),
            "themes": themes,
            "event_types": event_types,
            "guest_url": guest_url,
        },
    )


router.include_router(events_edit_submit_router)
router.include_router(events_locking_router)
