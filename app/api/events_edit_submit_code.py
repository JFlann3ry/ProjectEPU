from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.events_edit_submit_numeric import edit_event_submit
from app.core.templates import templates
from app.models.event import Event
from app.services.auth import require_user
from app.services.csrf import CSRF_COOKIE
from app.services.theme_values import build_theme_view, resolve_effective_theme
from db import get_db

router = APIRouter()


@router.post("/e/{code}/edit", response_class=HTMLResponse)
async def edit_event_submit_code(
    request: Request,
    code: str,
    name: str = Form(...),
    date: str = Form(None),
    event_type_id: str = Form(None),
    custom_event_type: str = Form(None),
    theme_id: str = Form(None),
    welcome_message: str = Form(None),
    upload_instructions: str = Form(None),
    remove_banner: str = Form(None),
    primary_color: str = Form(None),
    secondary_color: str = Form(None),
    text_color: str = Form(None),
    accent_color: str = Form(None),
    background_color: str = Form(None),
    input_background_color: str = Form(None),
    dropzone_background_color: str = Form(None),
    font_family: str = Form(None),
    button_style: str = Form(None),
    button_gradient_style: str = Form(None),
    button_gradient_direction: str = Form(None),
    corner_radius: str = Form(None),
    heading_size: str = Form(None),
    show_cover: str = Form(None),
    banner_image: UploadFile = File(None),
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    from app.models.event import EventCustomisation, EventType, Theme
    from app.services.csrf import issue_csrf_token, set_csrf_cookie, validate_csrf_token

    cookie_token = request.cookies.get(CSRF_COOKIE)
    if (
        not cookie_token
        or not csrf_token
        or not validate_csrf_token(csrf_token, request.cookies.get("session_id"))
        or cookie_token != csrf_token
    ):
        token = issue_csrf_token(request.cookies.get("session_id"))
        event = db.query(Event).filter(Event.Code == code).first()
        custom = (
            db.query(EventCustomisation).filter(EventCustomisation.EventID == event.EventID).first()
            if event
            else None
        )
        selected_theme = None
        try:
            if custom and getattr(custom, "ThemeID", None):
                selected_theme = db.query(Theme).filter(Theme.ThemeID == custom.ThemeID).first()
        except Exception:
            selected_theme = None
        effective_theme = resolve_effective_theme(custom, selected_theme)
        resp = templates.TemplateResponse(
            request,
            "edit_event.html",
            context={
                "event": event,
                "custom": custom,
                "effective_theme": effective_theme,
                "theme_view": build_theme_view(effective_theme),
                "themes": db.query(Theme).all(),
                "event_types": db.query(EventType).order_by(EventType.Name.asc()).all(),
                "guest_url": f"/guest/upload/{code}",
                "csrf_token": token,
                "error": "Invalid form token. Please refresh and try again.",
            },
            status_code=400,
        )
        set_csrf_cookie(resp, token, httponly=True)
        return resp
    # Resolve event by code, then delegate by calling the existing handler logic
    event = db.query(Event).filter(Event.Code == code).first()
    if not event:
        return RedirectResponse("/events", status_code=303)
    # Ownership check
    try:
        if getattr(event, "UserID", None) != getattr(user, "UserID", None):
            return RedirectResponse("/events", status_code=303)
    except Exception:
        pass
    # Delegate via numeric ID to keep behavior aligned in one place.
    event_id = int(getattr(event, "EventID"))
    return await edit_event_submit(
        request,
        event_id,
        name,
        date,
        event_type_id,
        custom_event_type,
        theme_id,
        welcome_message,
        upload_instructions,
        remove_banner,
        primary_color,
        secondary_color,
        text_color,
        accent_color,
        background_color,
        input_background_color,
        dropzone_background_color,
        font_family,
        button_style,
        button_gradient_style,
        button_gradient_direction,
        corner_radius,
        heading_size,
        show_cover,
        banner_image,
        csrf_token,
        db,
        user,
    )
