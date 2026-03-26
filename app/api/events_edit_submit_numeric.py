import logging
import os
import re
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func as _func
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.event import Event
from app.services.auth import require_user
from app.services.csrf import CSRF_COOKIE
from app.services.mime_utils import is_allowed_mime
from app.services.theme_values import (
    build_theme_view,
    normalize_button_style,
    normalize_gradient_direction,
    normalize_gradient_style,
    resolve_effective_theme,
)
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.post("/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_submit(
    request: Request,
    event_id: int,
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
        event = db.query(Event).filter(Event.EventID == event_id).first()
        custom = (
            db.query(EventCustomisation).filter(EventCustomisation.EventID == event_id).first()
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
                "guest_url": f"/guest/upload/{event.Code}" if event else None,
                "csrf_token": token,
                "error": "Invalid form token. Please refresh and try again.",
            },
            status_code=400,
        )
        set_csrf_cookie(resp, token, httponly=True)
        return resp
    event = db.query(Event).filter(Event.EventID == event_id).first()
    audit.info(
        "events.edit.submit",
        extra={
            "event_id": event_id,
            "user_id": getattr(user, "UserID", None),
            "client": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    if event:
        setattr(event, "Name", name)
        # Only allow date update if not locked
        if not getattr(event, "IsDateLocked", False):
            try:
                parsed_date = datetime.strptime(date, "%Y-%m-%d") if date else None
            except Exception:
                parsed_date = None
            setattr(event, "Date", parsed_date)
        # Event type selection (always editable)
        et_raw = str(event_type_id).strip() if isinstance(event_type_id, str) else None
        if et_raw == "other":
            # Create or reuse a custom EventType by name
            ct = (custom_event_type or "").strip()
            if ct:
                # Case-insensitive lookup to avoid dupes
                existing = (
                    db.query(EventType).filter(_func.lower(EventType.Name) == ct.lower()).first()
                )
                if existing:
                    setattr(event, "EventTypeID", existing.EventTypeID)
                else:
                    new_et = EventType(Name=ct)
                    db.add(new_et)
                    db.flush()  # Get PK without full commit.
                    try:
                        setattr(event, "EventTypeID", new_et.EventTypeID)
                    except Exception:
                        setattr(event, "EventTypeID", None)
            else:
                # No custom text provided; clear selection
                setattr(event, "EventTypeID", None)
        else:
            try:
                etid = int(et_raw) if et_raw and et_raw.isdigit() else None
            except Exception:
                etid = None
            if etid is None:
                setattr(event, "EventTypeID", None)
            else:
                # Validate existence
                exists = db.query(EventType).filter(EventType.EventTypeID == etid).first()
                setattr(event, "EventTypeID", etid if exists else None)
        db.commit()
    custom = db.query(EventCustomisation).filter(EventCustomisation.EventID == event_id).first()
    if not custom:
        custom = EventCustomisation(EventID=event_id)
        db.add(custom)
    # Theme handling: set ThemeID and copy theme defaults to customization fields
    selected_theme_id = None
    try:
        if theme_id:
            theme_id_str = str(theme_id).strip()
            if theme_id_str.isdigit():
                selected_theme_id = int(theme_id_str)
    except Exception:
        selected_theme_id = None
    setattr(custom, "ThemeID", selected_theme_id)
    if selected_theme_id:
        try:
            from app.models.event import Theme

            t = db.query(Theme).filter(Theme.ThemeID == selected_theme_id).first()
        except Exception:
            t = None
        if t:
            # Copy theme values; these can be overridden by posted custom colors below
            if getattr(t, "ButtonColour1", None):
                setattr(custom, "ButtonColour1", t.ButtonColour1)
            if getattr(t, "ButtonColour2", None):
                setattr(custom, "ButtonColour2", t.ButtonColour2)
            if getattr(t, "BackgroundColour", None):
                setattr(custom, "BackgroundColour", t.BackgroundColour)
            if getattr(t, "FontFamily", None):
                setattr(custom, "FontFamily", t.FontFamily)
            if getattr(t, "TextColour", None):
                setattr(custom, "TextColour", t.TextColour)
            if getattr(t, "AccentColour", None):
                setattr(custom, "AccentColour", t.AccentColour)
            try:
                setattr(
                    custom,
                    "ButtonStyle",
                    normalize_button_style(getattr(t, "ButtonStyle", None)),
                )
            except Exception:
                pass
            # New fields: input/dropzone backgrounds
            try:
                if getattr(t, "InputBackgroundColour", None):
                    setattr(custom, "InputBackgroundColour", t.InputBackgroundColour)
                if getattr(t, "DropzoneBackgroundColour", None):
                    setattr(custom, "DropzoneBackgroundColour", t.DropzoneBackgroundColour)
            except Exception:
                pass
    if welcome_message is not None:
        setattr(custom, "WelcomeMessage", welcome_message)
    if upload_instructions is not None:
        setattr(custom, "UploadInstructions", upload_instructions)
    if primary_color is not None:
        setattr(custom, "ButtonColour1", primary_color)
    if secondary_color is not None:
        setattr(custom, "ButtonColour2", secondary_color)
    if text_color is not None:
        setattr(custom, "TextColour", text_color)
    if accent_color is not None:
        setattr(custom, "AccentColour", accent_color)
    if background_color is not None:
        setattr(custom, "BackgroundColour", background_color)
    # Persist additional background surface colors for inputs and dropzone
    if input_background_color is not None:
        try:
            setattr(custom, "InputBackgroundColour", input_background_color)
        except Exception:
            pass
    if dropzone_background_color is not None:
        try:
            setattr(custom, "DropzoneBackgroundColour", dropzone_background_color)
        except Exception:
            pass
    if font_family is not None:
        setattr(custom, "FontFamily", font_family)
    # New options
    style_val = (
        normalize_button_style(button_style, default="") if button_style is not None else None
    )
    if style_val in ("gradient", "solid"):
        setattr(custom, "ButtonStyle", style_val)
    # Persist gradient parameters when provided
    grad_style = (
        normalize_gradient_style(button_gradient_style, default="")
        if button_gradient_style is not None
        else None
    )
    if grad_style in ("linear", "radial"):
        try:
            setattr(custom, "ButtonGradientStyle", grad_style)
        except Exception:
            pass
    grad_dir = (
        normalize_gradient_direction(button_gradient_direction, default="")
        if button_gradient_direction is not None
        else None
    )
    if grad_dir and grad_dir.endswith("deg"):
        try:
            setattr(custom, "ButtonGradientDirection", grad_dir)
        except Exception:
            pass
    if corner_radius in ("subtle", "rounded", "sharp"):
        setattr(custom, "CornerRadius", corner_radius)
    if heading_size in ("s", "m", "l"):
        setattr(custom, "HeadingSize", heading_size)
    # Checkbox comes as '1' when checked
    if show_cover is not None:
        setattr(custom, "ShowCover", True if str(show_cover) in ("1", "true", "on") else False)

    # QR colours - read from form to avoid changing function signature used by code-path delegate
    try:
        form = await request.form()
        qr_fill_val = form.get("qr_fill") if form is not None else None
        qr_back_val = form.get("qr_back") if form is not None else None
        qr_remove_logo_val = form.get("qr_remove_logo") if form is not None else None
        if qr_fill_val is not None:
            setattr(custom, "QRFillColour", (str(qr_fill_val) or "").strip() or None)
        if qr_back_val is not None:
            setattr(custom, "QRBackColour", (str(qr_back_val) or "").strip() or None)
        # Checkbox posts 'on' or '1' when checked; absent when unchecked. Normalize.
        try:
            if qr_remove_logo_val is not None:
                val = str(qr_remove_logo_val)
                setattr(custom, "RemoveWebsiteLogo", val in ("1", "on", "true"))
            else:
                # Explicit unchecked: ensure false when checkbox absent in some clients
                setattr(custom, "RemoveWebsiteLogo", False)
        except Exception:
            pass
    except Exception:
        pass

    # Validation helpers for image assets
    def _safe_name(name: str) -> str:
        name = name.replace("\\", "/").split("/")[-1]
        return re.sub(r"[^A-Za-z0-9._-]", "_", name)

    max_bytes = int(getattr(settings, "MAX_UPLOAD_BYTES", 200_000_000))

    if banner_image and banner_image.filename:
        fallback = getattr(banner_image, "content_type", "") or ""
        data = await banner_image.read()
        allowed, sniffed = is_allowed_mime(
            data,
            allowed_prefixes=("image/",),
            fallback_content_type=fallback,
        )
        if not allowed:
            audit.warning(
                "events.edit.asset.banner_rejected_mime",
                extra={
                    "event_id": event_id,
                    "ctype": sniffed,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
        elif max_bytes and len(data) > max_bytes:
            audit.warning(
                "events.edit.asset.banner_rejected_size",
                extra={
                    "event_id": event_id,
                    "size": len(data),
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
        else:
            safe = _safe_name(banner_image.filename)
            banner_path = f"static/uploads/event_{event_id}_banner_{safe}"
            os.makedirs(os.path.dirname(banner_path), exist_ok=True)
            with open(banner_path, "wb") as buffer:
                buffer.write(data)
            setattr(custom, "CoverPhotoPath", f"/{banner_path}")
            # Ensure cover is shown if a banner exists
            try:
                setattr(custom, "ShowCover", True)
            except Exception:
                pass
            try:
                audit.info(
                    "events.edit.asset.banner_updated",
                    extra={
                        # Avoid reserved LogRecord keys like `filename`.
                        "event_id": event_id,
                        "file_name": getattr(banner_image, "filename", None),
                        "request_id": getattr(request.state, "request_id", None),
                    },
                )
            except Exception:
                # Never let logging failures block the request.
                pass
    # Handle explicit banner removal when requested and no new banner was uploaded
    try:
        if remove_banner and str(remove_banner).strip().lower() in ("1", "true", "on"):
            if not (banner_image and getattr(banner_image, "filename", None)):
                try:
                    setattr(custom, "CoverPhotoPath", None)
                except Exception:
                    pass
                try:
                    setattr(custom, "ShowCover", False)
                except Exception:
                    pass
    except Exception:
        pass
    db.commit()
    # After save, prefer code-based URL to avoid exposing numeric IDs
    try:
        code = getattr(event, "Code", None)
    except Exception:
        code = None
    if code:
        return RedirectResponse(f"/e/{code}/edit", status_code=303)
    # Fallback to legacy URL
    return RedirectResponse(f"/events/{event_id}/edit", status_code=303)
