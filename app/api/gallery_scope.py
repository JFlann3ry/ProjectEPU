from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.gallery_scope_shared import GALLERY_COOKIE, _sign_scope
from app.core.settings import settings
from app.models.event import Event
from app.services.auth import require_user
from app.services.csrf import validate_csrf_token
from db import get_db

router = APIRouter()


@router.post("/gallery/select")
async def select_gallery_event(
    request: Request,
    event_id: int = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Persist selected event for gallery via a signed cookie and redirect to /gallery.

    Ownership is strictly enforced; CSRF is best-effort if supplied.
    """
    # Determine if this is a fetch/XHR request to tailor response type
    is_fetch = False
    try:
        xrw = request.headers.get("X-Requested-With", "") or ""
        # We set 'fetch' in callers; also handle generic XHR
        is_fetch = xrw.lower() in ("fetch", "xmlhttprequest")
    except Exception:
        is_fetch = False

    # Best-effort CSRF check
    try:
        sid = request.cookies.get("session_id")
        if csrf_token and sid and not validate_csrf_token(csrf_token, sid):
            if is_fetch:
                return JSONResponse({"ok": False, "error": "csrf"}, status_code=400)
            else:
                resp = RedirectResponse(url="/gallery", status_code=303)
                return resp
    except Exception:
        pass
    # Ownership check
    owned = (
        db.query(Event.EventID)
        .filter(Event.EventID == int(event_id), Event.UserID == user.UserID)
        .first()
    )
    resp = RedirectResponse(url="/gallery", status_code=303)
    if not owned:
        if is_fetch:
            # Clear any stale cookie and return JSON error
            j = JSONResponse({"ok": False, "error": "not_owned"}, status_code=403)
            j.delete_cookie(GALLERY_COOKIE, path="/")
            return j
        else:
            resp.delete_cookie(GALLERY_COOKIE, path="/")
            return resp
    value = _sign_scope(str(int(event_id)))
    if is_fetch:
        j = JSONResponse({"ok": True})
        j.set_cookie(
            key=GALLERY_COOKIE,
            value=value,
            httponly=True,
            samesite="lax",
            secure=bool(getattr(settings, "COOKIE_SECURE", False)),
            max_age=60 * 60 * 6,
            path="/",
        )
        return j
    else:
        resp.set_cookie(
            key=GALLERY_COOKIE,
            value=value,
            httponly=True,
            samesite="lax",
            secure=bool(getattr(settings, "COOKIE_SECURE", False)),
            max_age=60 * 60 * 6,
            path="/",
        )
        return resp


@router.post("/gallery/clear")
async def clear_gallery_event():
    resp = RedirectResponse(url="/gallery", status_code=303)
    resp.delete_cookie(GALLERY_COOKIE, path="/")
    return resp
