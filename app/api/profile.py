from typing import Any  # noqa: I001

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.services import auth
from app.services.auth import get_current_user
from app.services.csrf import issue_csrf_token, set_csrf_cookie, validate_csrf_token
from db import get_db

router = APIRouter()


def get_current_user_id(request: Request, db: Session) -> int | None:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    session_obj = auth.get_session(db=db, session_id=session_id)
    if not session_obj:
        return None
    uid: Any = getattr(session_obj, "UserID", None)
    if isinstance(uid, int):
        return uid
    try:
        return int(str(uid)) if uid is not None else None
    except Exception:
        return None


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    # Get plan for badge
    plan, features = (None, {})
    try:
        from app.services.billing_utils import get_active_plan

        plan, features = get_active_plan(db, getattr(user, "UserID", 0))
    except Exception:
        plan, features = (None, {})
    # Fetch email prefs for modal defaults
    from app.models.user_prefs import UserEmailPreference

    prefs_row = (
        db.query(UserEmailPreference)
        .filter(UserEmailPreference.UserID == getattr(user, "UserID", None))
        .first()
    )
    email_prefs = {
        "marketing": bool(getattr(prefs_row, "MarketingOptIn", False)) if prefs_row else False,
        "product": bool(getattr(prefs_row, "ProductUpdatesOptIn", False)) if prefs_row else False,
        "reminders": bool(getattr(prefs_row, "EventRemindersOptIn", True)) if prefs_row else True,
    }
    # Quick stats and upcoming
    events_count = 0
    uploads_count = 0
    recent_events = []
    next_event = None
    try:
        from app.models.event import Event, FileMetadata as FM  # noqa: I001 - local import
        from datetime import datetime, timezone

        uid = int(getattr(user, "UserID", 0) or 0)
        events_count = db.query(Event).filter(Event.UserID == uid).count()
        uploads_count = (
            db.query(FM)
            .join(Event, FM.EventID == Event.EventID)
            .filter(Event.UserID == uid)
            .count()
        )
        # Only show past events (with a Date set and strictly before now)
        now = datetime.now(timezone.utc)
        recent_events = (
            db.query(Event)
            .filter(
                Event.UserID == uid,
                Event.Date != None,  # noqa: E711
                Event.Date < now,
            )
            .order_by(Event.Date.desc())
            .limit(3)
            .all()
        )
        # Next upcoming event (by Date in the future)
        nxt = (
            db.query(Event)
            .filter(Event.UserID == uid, Event.Date != None, Event.Date >= now)  # noqa: E711
            .order_by(Event.Date.asc())
            .first()
        )
        if nxt and getattr(nxt, "Date", None):
            dt = getattr(nxt, "Date")
            # Ensure timezone-aware comparison; if naive, assume UTC
            if getattr(dt, "tzinfo", None) is None:
                dt = dt.replace(tzinfo=timezone.utc)
            remaining = (dt - now).total_seconds()
            days_until = int((remaining + 86399) // 86400) if remaining >= 0 else 0
            when_disp = dt.strftime("%a, %b %d, %Y")
            next_event = {
                "id": getattr(nxt, "EventID", 0),
                "name": getattr(nxt, "Name", "Event"),
                "when": when_disp,
                "date_iso": dt.isoformat(),
                "days_until": days_until,
                # Add fields used by profile share modal
                "code": getattr(nxt, "Code", ""),
                "published": bool(getattr(nxt, "Published", False)),
            }
    except Exception:
        events_count = 0
        uploads_count = 0
        recent_events = []
        next_event = None

    token = issue_csrf_token(request.cookies.get("session_id"))
    resp = templates.TemplateResponse(
        request,
        "profile.html",
        context={
            "user": user,
            "plan": plan,
            "features": features,
            "events_count": events_count,
            "uploads_count": uploads_count,
            "recent_events": recent_events,
            "csrf_token": token,
            "email_prefs": email_prefs,
            "next_event": next_event,
        },
    )
    # Set CSRF cookie for form POST verification
    set_csrf_cookie(resp, token, httponly=False)
    return resp


@router.get("/profile/email-preferences", response_class=HTMLResponse)
async def email_prefs_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    from app.models.user_prefs import UserEmailPreference  # noqa: I001 - local import

    prefs = (
        db.query(UserEmailPreference)
        .filter(UserEmailPreference.UserID == getattr(user, "UserID", None))
        .first()
    )
    # Defaults if no row yet
    data = {
        "marketing": bool(getattr(prefs, "MarketingOptIn", False)) if prefs else False,
        "product": bool(getattr(prefs, "ProductUpdatesOptIn", False)) if prefs else False,
        "reminders": bool(getattr(prefs, "EventRemindersOptIn", True)) if prefs else True,
    }
    notice = request.query_params.get("notice") if request.query_params else None
    token = issue_csrf_token(request.cookies.get("session_id"))
    resp = templates.TemplateResponse(
        request,
        "email_prefs.html",
        context={"prefs": data, "notice": notice, "csrf_token": token},
    )
    set_csrf_cookie(resp, token, httponly=False)
    return resp


@router.post("/profile/email-preferences", response_class=HTMLResponse)
async def email_prefs_submit(
    request: Request,
    marketing: str | None = Form(None),
    product: str | None = Form(None),
    reminders: str | None = Form(None),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    # CSRF check
    sid = request.cookies.get("session_id")
    if not csrf_token or not validate_csrf_token(csrf_token, sid):
        return RedirectResponse("/profile/email-preferences?notice=invalid", status_code=303)
    from app.models.user_prefs import UserEmailPreference

    row = (
        db.query(UserEmailPreference)
        .filter(UserEmailPreference.UserID == getattr(user, "UserID", None))
        .first()
    )
    if not row:
        row = UserEmailPreference(UserID=getattr(user, "UserID", None))
        db.add(row)
    setattr(row, "MarketingOptIn", bool(marketing))
    setattr(row, "ProductUpdatesOptIn", bool(product))
    setattr(row, "EventRemindersOptIn", bool(reminders))
    db.commit()
    return RedirectResponse("/profile/email-preferences?notice=saved", status_code=303)


@router.post("/profile/email-preferences/unsubscribe", response_class=HTMLResponse)
async def email_prefs_unsubscribe(
    request: Request,
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    # CSRF check
    sid = request.cookies.get("session_id")
    if not csrf_token or not validate_csrf_token(csrf_token, sid):
        return RedirectResponse("/profile/email-preferences?notice=invalid", status_code=303)
    from app.models.user_prefs import UserEmailPreference

    row = (
        db.query(UserEmailPreference)
        .filter(UserEmailPreference.UserID == getattr(user, "UserID", None))
        .first()
    )
    if not row:
        row = UserEmailPreference(UserID=getattr(user, "UserID", None))
        db.add(row)
    # Clear all toggles
    setattr(row, "MarketingOptIn", False)
    setattr(row, "ProductUpdatesOptIn", False)
    setattr(row, "EventRemindersOptIn", False)
    db.commit()
    return RedirectResponse("/profile/email-preferences?notice=unsubscribed", status_code=303)
