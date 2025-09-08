import io as _io
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from PIL import Image
from sqlalchemy import func as _func
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.addons import AddonCatalog
from app.models.event import (
    Event,
    EventCustomisation,
    EventType,
    FileMetadata,
    GuestSession,
    Theme,
)
from app.services.auth import require_user
from app.services.email_utils import send_event_date_locked_email
from app.services.mime_utils import is_allowed_mime
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.get("/e/{code}/edit", response_class=HTMLResponse)
async def edit_event_page_code(
    request: Request, code: str, db: Session = Depends(get_db), user=Depends(require_user)
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
        db.query(EventCustomisation)
        .filter(EventCustomisation.EventID == event.EventID)
        .first()
    )
    from app.models.event import Theme

    themes = db.query(Theme).all()
    event_types = db.query(EventType).order_by(EventType.Name.asc()).all()
    guest_url = f"/guest/upload/{event.Code}" if event else None
    return templates.TemplateResponse(
        request,
        "edit_event.html",
        context={
            "event": event,
            "custom": custom,
            "themes": themes,
            "event_types": event_types,
            "guest_url": guest_url,
        },
    )

@router.get("/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_page(
    request: Request, event_id: int, db: Session = Depends(get_db), user=Depends(require_user)
):
    # Compatibility: redirect numeric ID URL to code-based path if possible
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if event and getattr(event, "Code", None):
        return RedirectResponse(f"/e/{event.Code}/edit", status_code=307)
    # Fallback to legacy render
    custom = (
        db.query(EventCustomisation)
        .filter(EventCustomisation.EventID == event_id)
        .first()
    )
    from app.models.event import Theme

    themes = db.query(Theme).all()
    event_types = db.query(EventType).order_by(EventType.Name.asc()).all()
    guest_url = f"/guest/upload/{event.Code}" if event else None
    return templates.TemplateResponse(
        request,
        "edit_event.html",
        context={
            "event": event,
            "custom": custom,
            "themes": themes,
            "event_types": event_types,
            "guest_url": guest_url,
        },
    )


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
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
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
        et_raw = (str(event_type_id).strip() if isinstance(event_type_id, str) else None)
        if et_raw == "other":
            # Create or reuse a custom EventType by name
            ct = (custom_event_type or "").strip()
            if ct:
                # Case-insensitive lookup to avoid dupes
                existing = (
                    db.query(EventType)
                    .filter(_func.lower(EventType.Name) == ct.lower())
                    .first()
                )
                if existing:
                    setattr(event, "EventTypeID", existing.EventTypeID)
                else:
                    new_et = EventType(Name=ct)
                    db.add(new_et)
                    db.flush()  # get pk without full commit
                    try:
                        setattr(event, "EventTypeID", new_et.EventTypeID)
                    except Exception:
                        setattr(event, "EventTypeID", None)
            else:
                # No custom text provided; clear selection
                setattr(event, "EventTypeID", None)
        else:
            try:
                etid = (
                    int(et_raw)
                    if et_raw and et_raw.isdigit()
                    else None
                )
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
    # theme_id comes as str; treat empty as None
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
    if button_style in ("gradient", "solid"):
        setattr(custom, "ButtonStyle", button_style)
    # Persist gradient parameters when provided
    if button_gradient_style in ("linear", "radial"):
        try:
            setattr(custom, "ButtonGradientStyle", button_gradient_style)
        except Exception:
            pass
    if isinstance(button_gradient_direction, str) and button_gradient_direction.endswith("deg"):
        try:
            setattr(custom, "ButtonGradientDirection", button_gradient_direction)
        except Exception:
            pass
    if corner_radius in ("subtle", "rounded", "sharp"):
        setattr(custom, "CornerRadius", corner_radius)
    if heading_size in ("s", "m", "l"):
        setattr(custom, "HeadingSize", heading_size)
    # Checkbox comes as '1' when checked
    if show_cover is not None:
        setattr(custom, "ShowCover", True if str(show_cover) in ("1", "true", "on") else False)

    # Validation helpers for image assets
    def _safe_name(name: str) -> str:
        name = name.replace("\\", "/").split("/")[-1]
        return re.sub(r"[^A-Za-z0-9._-]", "_", name)

    max_bytes = int(getattr(settings, "MAX_UPLOAD_BYTES", 200_000_000))

    # Removed: unused logo_image upload support

    if banner_image and banner_image.filename:
        fallback = getattr(banner_image, "content_type", "") or ""
        data = await banner_image.read()
        allowed, sniffed = is_allowed_mime(
            data, allowed_prefixes=("image/",), fallback_content_type=fallback
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
                        "event_id": event_id,
                        # Note: avoid reserved LogRecord keys like 'filename', 'lineno', etc.
                        # Using 'filename' here raises KeyError in logging.makeRecord.
                        "file_name": getattr(banner_image, "filename", None),
                        "request_id": getattr(request.state, "request_id", None),
                    },
                )
            except Exception:
                # Never let logging failures block the request
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
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
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
    # Call the existing logic by passing through to the numeric-id handler body
    # Easiest safe reuse: call the function logic inline by duplicating a small wrapper
    # Delegate using numeric ID for reuse of validation and saving logic
    event_id = int(getattr(event, "EventID"))
    # Reuse the same parameter names and behavior by calling the internal code path
    # For maintainability, we could refactor into a shared helper, but inline is minimal-risk here.
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
        db,
        user,
    )


@router.post("/events/{event_id}/lock-date", response_class=HTMLResponse)
async def lock_event_date(
    request: Request, event_id: int, db: Session = Depends(get_db), user=Depends(require_user)
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

            setattr(event, "DateLockedAt", _dt.utcnow())
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
                # user dependency is the locker; ensure we have their email
                to_email = getattr(user, "Email", None)
            except Exception:
                to_email = None
            if to_email:
                # Build a friendly date string and dashboard URL
                date_str = ""
                try:
                    d = getattr(event, "Date", None)
                    date_str = d.strftime("%d-%m-%Y") if d else ""
                except Exception:
                    pass
                base_url = str(request.base_url).rstrip("/")
                dash_url = f"{base_url}/events/{event.EventID}"
                # Fire and forget
                await send_event_date_locked_email(
                    to_email, getattr(event, "Name", "Your Event"), date_str, dash_url
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
    return RedirectResponse(f"/events/{event_id}", status_code=303)


@router.get("/events/code/{code}", response_class=HTMLResponse)
async def owner_event_details_by_code(
    request: Request, code: str, db: Session = Depends(get_db), user=Depends(require_user)
):
    event = db.query(Event).filter(Event.Code == code).first()
    if not event:
        return RedirectResponse("/events", status_code=303)
    try:
        if getattr(event, "UserID", None) != getattr(user, "UserID", None):
            return RedirectResponse("/events", status_code=303)
    except Exception:
        pass
    # Render the same details template as numeric route
    event_id = int(getattr(event, "EventID"))
    custom = (
        db.query(EventCustomisation).filter(EventCustomisation.EventID == event_id).first()
    )
    event_type = (
        db.query(EventType).filter(EventType.EventTypeID == event.EventTypeID).first()
        if event
        else None
    )
    guest_url = f"/guest/upload/{event.Code}" if event else None
    qr_url = f"{str(request.base_url)}guest/upload/{event.Code}" if event else None
    canonical_url = None
    try:
        canonical_url = f"{str(request.base_url).rstrip('/')}/events/code/{code}"
    except Exception:
        canonical_url = None
    # Messages
    messages = []
    try:
        from app.models.event import GuestMessage, GuestSession

        rows = (
            db.query(GuestMessage, GuestSession.GuestEmail)
            .outerjoin(GuestSession, GuestSession.GuestID == GuestMessage.GuestSessionID)
            .filter(GuestMessage.EventID == event_id)
            .order_by(GuestMessage.CreatedAt.desc())
            .limit(200)
            .all()
        )
        for gm, email in rows:
            try:
                setattr(gm, "GuestEmail", email)
            except Exception:
                pass
            messages.append(gm)
    except Exception:
        messages = []
    # Extras
    extras = []
    try:
        rows = (
            db.query(AddonCatalog)
            .filter(AddonCatalog.IsActive == True)  # noqa: E712
            .order_by(AddonCatalog.PriceCents.asc())
            .limit(6)
            .all()
        )
        for a in rows:
            try:
                extras.append(
                    {
                        "id": int(getattr(a, "AddonID")),
                        "code": str(getattr(a, "Code")),
                        "name": str(getattr(a, "Name")),
                        "desc": str(getattr(a, "Description") or ""),
                        "price_cents": int(getattr(a, "PriceCents") or 0),
                        "currency": (getattr(a, "Currency") or "gbp").lower(),
                        "allow_qty": bool(getattr(a, "AllowQuantity")),
                        "min_qty": int(getattr(a, "MinQuantity") or 1),
                        "max_qty": int(getattr(a, "MaxQuantity") or 1),
                    }
                )
            except Exception:
                pass
    except Exception:
        extras = []
    # Upload stats
    upload_stats = {"total": 0, "images": 0, "videos": 0, "unique_uploaders": 0}
    try:
        base = db.query(FileMetadata).filter(
            FileMetadata.EventID == int(event_id), ~FileMetadata.Deleted
        )
        upload_stats["total"] = int(base.count())
        upload_stats["images"] = int(
            base.filter(FileMetadata.FileType.like("image%"))
            .with_entities(_func.count())
            .scalar()
            or 0
        )
        upload_stats["videos"] = int(
            base.filter(FileMetadata.FileType.like("video%"))
            .with_entities(_func.count())
            .scalar()
            or 0
        )
        upload_stats["unique_uploaders"] = int(
            db.query(_func.count(_func.distinct(FileMetadata.GuestID)))
            .filter(
                FileMetadata.EventID == int(event_id),
                ~FileMetadata.Deleted,
                FileMetadata.GuestID.isnot(None),
            )
            .scalar()
            or 0
        )
    except Exception:
        upload_stats = {"total": 0, "images": 0, "videos": 0, "unique_uploaders": 0}
    return templates.TemplateResponse(
        request,
        "event_details.html",
        context={
            "event": event,
            "event_type": event_type,
            "custom": custom,
            "guest_url": guest_url,
            "qr_url": qr_url,
            "canonical_url": canonical_url,
            "messages": messages,
            "extras": extras,
            "upload_stats": upload_stats,
            "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )
    
@router.get("/events/{event_id}", response_class=HTMLResponse)
async def event_details(
    request: Request, event_id: int, db: Session = Depends(get_db), user=Depends(require_user)
):
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if event and getattr(event, "Code", None):
        return RedirectResponse(f"/events/code/{event.Code}", status_code=307)
    custom = db.query(EventCustomisation).filter(EventCustomisation.EventID == event_id).first()
    event_type = (
        db.query(EventType).filter(EventType.EventTypeID == event.EventTypeID).first()
        if event
        else None
    )
    # Deep link straight to the upload page (no intermediate login form)
    guest_url = f"/guest/upload/{event.Code}" if event else None
    qr_url = f"{str(request.base_url)}guest/upload/{event.Code}" if event else None
    canonical_url = None
    try:
        canonical_url = f"{str(request.base_url).rstrip('/')}/events/{event_id}"
    except Exception:
        canonical_url = None
    # Load recent guest messages for this event (owner view)
    messages = []
    try:
        from app.models.event import GuestMessage, GuestSession

        if event:
            rows = (
                db.query(GuestMessage, GuestSession.GuestEmail)
                .outerjoin(GuestSession, GuestSession.GuestID == GuestMessage.GuestSessionID)
                .filter(GuestMessage.EventID == int(getattr(event, "EventID")))
                .order_by(GuestMessage.CreatedAt.desc())
                .limit(200)
                .all()
            )
            for gm, email in rows:
                try:
                    setattr(gm, "GuestEmail", email)
                except Exception:
                    pass
                messages.append(gm)
    except Exception:
        messages = []
    # Active add-ons (extras) for purchase
    extras = []
    try:
        rows = (
            db.query(AddonCatalog)
            .filter(AddonCatalog.IsActive == True)  # noqa: E712
            .order_by(AddonCatalog.PriceCents.asc())
            .limit(6)
            .all()
        )
        for a in rows:
            try:
                extras.append(
                    {
                        "id": int(getattr(a, "AddonID")),
                        "code": str(getattr(a, "Code")),
                        "name": str(getattr(a, "Name")),
                        "desc": str(getattr(a, "Description") or ""),
                        "price_cents": int(getattr(a, "PriceCents") or 0),
                        "currency": (getattr(a, "Currency") or "gbp").lower(),
                        "allow_qty": bool(getattr(a, "AllowQuantity")),
                        "min_qty": int(getattr(a, "MinQuantity") or 1),
                        "max_qty": int(getattr(a, "MaxQuantity") or 1),
                    }
                )
            except Exception:
                pass
    except Exception:
        extras = []

    # Upload stats for this event: totals for images/videos and unique guest uploaders
    upload_stats = {"total": 0, "images": 0, "videos": 0, "unique_uploaders": 0}
    try:

        base = db.query(FileMetadata).filter(
            FileMetadata.EventID == int(event_id), ~FileMetadata.Deleted
        )
        upload_stats["total"] = int(base.count())
        upload_stats["images"] = int(
            base.filter(FileMetadata.FileType.like("image%"))
            .with_entities(_func.count())
            .scalar()
            or 0
        )
        upload_stats["videos"] = int(
            base.filter(FileMetadata.FileType.like("video%"))
            .with_entities(_func.count())
            .scalar()
            or 0
        )
        upload_stats["unique_uploaders"] = int(
            db.query(_func.count(_func.distinct(FileMetadata.GuestID)))
            .filter(
                FileMetadata.EventID == int(event_id),
                ~FileMetadata.Deleted,
                FileMetadata.GuestID.isnot(None),
            )
            .scalar()
            or 0
        )
    except Exception:
        upload_stats = {"total": 0, "images": 0, "videos": 0, "unique_uploaders": 0}

    return templates.TemplateResponse(
        request,
        "event_details.html",
        context={
            "event": event,
            "event_type": event_type,
            "custom": custom,
            "guest_url": guest_url,
            "qr_url": qr_url,
            "canonical_url": canonical_url,
            "messages": messages,
            "extras": extras,
            "upload_stats": upload_stats,
            "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )


@router.post("/events/{event_id}/qr/logo")
async def upload_qr_logo(
    request: Request,
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if not event:
        from fastapi.responses import JSONResponse

        return JSONResponse({"ok": False, "error": "Event not found"}, status_code=404)
    # Ownership check
    try:
        if getattr(event, "UserID", None) != getattr(user, "UserID", None):
            from fastapi.responses import JSONResponse

            return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)
    except Exception:
        from fastapi.responses import JSONResponse

        return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)
    # Validate
    if not file or not file.filename:
        from fastapi.responses import JSONResponse

        return JSONResponse({"ok": False, "error": "No file"}, status_code=400)
    ctype = getattr(file, "content_type", "") or ""
    if not (ctype.startswith("image/")):
        from fastapi.responses import JSONResponse

        return JSONResponse({"ok": False, "error": "Unsupported type"}, status_code=400)
    data = await file.read()
    if len(data) > 512 * 1024:
        from fastapi.responses import JSONResponse

        return JSONResponse({"ok": False, "error": "File too large"}, status_code=400)
    # Save under static/uploads/qrs/{event_id}/logo.png
    project_root = Path(__file__).resolve().parents[2]
    out_dir = project_root / "static" / "uploads" / "qrs" / str(event_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    try:
        img = Image.open(_io.BytesIO(data)).convert("RGBA")
        img.save(out_path, format="PNG")
    except Exception:
        out_path.write_bytes(data)
    rel = "/static/uploads/qrs/" + str(event_id) + "/logo.png"
    from fastapi.responses import JSONResponse

    return JSONResponse({"ok": True, "path": rel})


@router.post("/events/{event_id}/guestbook/{message_id}/delete")
async def guestbook_delete(
    request: Request,
    event_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Owner-only soft delete
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if not event:
        return RedirectResponse("/events", status_code=303)
    try:
        owner_id = getattr(event, "UserID", None)
        if owner_id is not None and owner_id != getattr(user, "UserID", None):
            return RedirectResponse(f"/events/{event_id}", status_code=303)
    except Exception:
        return RedirectResponse(f"/events/{event_id}", status_code=303)
    try:
        from app.models.event import GuestMessage

        gm = (
            db.query(GuestMessage)
            .filter(GuestMessage.GuestMessageID == message_id, GuestMessage.EventID == event_id)
            .first()
        )
        if gm:
            setattr(gm, "Deleted", True)
            db.commit()
            audit.info(
                "events.guestbook.delete",
                extra={
                    "event_id": event_id,
                    "message_id": message_id,
                    "user_id": getattr(user, "UserID", None),
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
    except Exception:
        pass
    return RedirectResponse(f"/events/{event_id}", status_code=303)


@router.post("/events/{event_id}/guestbook/{message_id}/restore")
async def guestbook_restore(
    request: Request,
    event_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Owner-only restore
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if not event:
        return RedirectResponse("/events", status_code=303)
    try:
        owner_id = getattr(event, "UserID", None)
        if owner_id is not None and owner_id != getattr(user, "UserID", None):
            return RedirectResponse(f"/events/{event_id}", status_code=303)
    except Exception:
        return RedirectResponse(f"/events/{event_id}", status_code=303)
    try:
        from app.models.event import GuestMessage

        gm = (
            db.query(GuestMessage)
            .filter(GuestMessage.GuestMessageID == message_id, GuestMessage.EventID == event_id)
            .first()
        )
        if gm:
            setattr(gm, "Deleted", False)
            db.commit()
            audit.info(
                "events.guestbook.restore",
                extra={
                    "event_id": event_id,
                    "message_id": message_id,
                    "user_id": getattr(user, "UserID", None),
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
    except Exception:
        pass
    return RedirectResponse(f"/events/{event_id}", status_code=303)


@router.get("/events", response_class=HTMLResponse)
async def events_dashboard(
    request: Request, db: Session = Depends(get_db), user=Depends(require_user)
):
    events = db.query(Event).filter(Event.UserID == user.UserID).all()
    # Annotate event type names
    try:
        ids = []
        for e in events:
            try:
                k = getattr(e, "EventTypeID", None)
                if isinstance(k, int):
                    ids.append(k)
            except Exception:
                pass
        ids = list(set(ids))
        type_map = {}
        if ids:
            types = db.query(EventType).filter(EventType.EventTypeID.in_(ids)).all()
            for t in types:
                try:
                    val = getattr(t, "EventTypeID", None)
                    nm = getattr(t, "Name", None)
                    if isinstance(val, int):
                        type_map[val] = nm
                except Exception:
                    pass
        for e in events:
            nm = None
            try:
                k = getattr(e, "EventTypeID", None)
                if isinstance(k, int):
                    nm = type_map.get(k)
            except Exception:
                nm = None
            setattr(e, "EventTypeName", nm)
    except Exception:
        for e in events:
            setattr(e, "EventTypeName", None)
    # Annotate guest counts
    try:

        counts = (
            db.query(GuestSession.EventID, _func.count(GuestSession.GuestID))
            .filter(GuestSession.EventID.in_([e.EventID for e in events]))
            .group_by(GuestSession.EventID)
            .all()
        )
        by_event = {eid: cnt for (eid, cnt) in counts}
        for e in events:
            setattr(e, "GuestCount", int(by_event.get(getattr(e, "EventID"), 0)))
    except Exception:
        for e in events:
            setattr(e, "GuestCount", None)
    # Annotate cover/banner image and cover visibility from EventCustomisation
    try:

        ec_rows = (
            db.query(EventCustomisation)
            .filter(EventCustomisation.EventID.in_([e.EventID for e in events]))
            .all()
        )
        ec_by_event = {row.EventID: row for row in ec_rows}

        # Theme fallback map (only fetch themes that are referenced)
        theme_ids = list(
            {
                getattr(r, "ThemeID", None)
                for r in ec_rows
                if getattr(r, "ThemeID", None)
            }
        )
        theme_map = {}
        if theme_ids:
            themes = db.query(Theme).filter(Theme.ThemeID.in_(theme_ids)).all()
            for t in themes:
                try:
                    theme_map[getattr(t, "ThemeID")] = t
                except Exception:
                    pass

        for e in events:
            row = ec_by_event.get(getattr(e, "EventID"))
            cover = None
            show_cover = True
            if row is not None:
                try:
                    cover = getattr(row, "CoverPhotoPath", None)
                except Exception:
                    cover = None
                try:
                    show_cover = bool(getattr(row, "ShowCover", True))
                except Exception:
                    show_cover = True
                # If no custom cover, try theme-provided cover/background
                if not cover:
                    try:
                        tid = getattr(row, "ThemeID", None)
                        t = theme_map.get(tid) if tid else None
                        if t is not None:
                            cover = (
                                getattr(t, "CoverPhotoPath", None)
                                or getattr(t, "BackgroundImage", None)
                            )
                    except Exception:
                        pass
            setattr(e, "CoverPhotoPath", cover)
            setattr(e, "ShowCover", show_cover)
    except Exception:
        for e in events:
            setattr(e, "CoverPhotoPath", None)
            setattr(e, "ShowCover", True)
    # Annotate storage usage (MB) if EventStorage present
    try:
        from app.models.event import EventStorage

        usage_rows = (
            db.query(EventStorage.EventID, _func.max(EventStorage.CurrentUsageMB))
            .filter(EventStorage.EventID.in_([e.EventID for e in events]))
            .group_by(EventStorage.EventID)
            .all()
        )
        usage_by_event = {eid: (int(usage or 0)) for (eid, usage) in usage_rows}
        for e in events:
            setattr(e, "StorageUsageMB", usage_by_event.get(getattr(e, "EventID"), 0))
    except Exception:
        for e in events:
            setattr(e, "StorageUsageMB", None)
    # Annotate checklist flags (SharedOnce)
    try:
        from app.models.event import EventChecklist as EC

        rows = db.query(EC).filter(EC.EventID.in_([e.EventID for e in events])).all()
        by_event = {r.EventID: bool(getattr(r, "SharedOnce", False)) for r in rows}
        for e in events:
            setattr(e, "SharedOnce", bool(by_event.get(getattr(e, "EventID"), False)))
    except Exception:
        for e in events:
            setattr(e, "SharedOnce", False)
    # Plan badge
    plan, features = (None, {})
    try:
        from app.services.billing_utils import get_active_plan

        plan, features = get_active_plan(db, getattr(user, "UserID", 0))
    except Exception:
        plan, features = (None, {})
    # Usage metrics
    total_events = len(events)
    # Plan-aware create disablement
    can_create = True
    block_reason = None
    try:
        # Local parse to avoid extra imports
        def _int(x):
            try:
                return max(0, int(x or 0))
            except Exception:
                return 0

        pf = features if isinstance(features, dict) else {}
        cap = _int(pf.get("max_events", 0))
        if cap > 0 and total_events >= cap:
            can_create = False
            block_reason = f"Event limit reached ({total_events}/{cap})."
    except Exception:
        can_create, block_reason = True, None
    return templates.TemplateResponse(
        request,
        "events_dashboard.html",
        context={
            "events": events,
            "plan": plan,
            "features": features,
            "total_events": total_events,
            "can_create": can_create,
            "create_block_reason": block_reason,
        },
    )


@router.post("/events/{event_id}/mark-shared")
async def mark_event_shared(
    request: Request, event_id: int, db: Session = Depends(get_db), user=Depends(require_user)
):
    # Mark checklist SharedOnce true
    try:
        from app.models.event import EventChecklist as EC

        row = db.query(EC).filter(EC.EventID == event_id).first()
        if not row:
            row = EC(EventID=event_id, SharedOnce=True)
            db.add(row)
        else:
            setattr(row, "SharedOnce", True)
        db.commit()
    except Exception:
        pass
    return {"ok": True}


# Public share page by event code (no auth, for SEO and sharing)
@router.get("/e/{code}", response_class=HTMLResponse)
async def public_event_share(
    request: Request, code: str, db: Session = Depends(get_db)
):
    # Fetch event by code regardless of publish state, then gate access
    ev = db.query(Event).filter(Event.Code == code).first()
    if not ev:
        return templates.TemplateResponse(request, "404.html", status_code=404)
    # If unpublished, only the owner may preview the share page
    is_owner_preview = False
    try:
        if not getattr(ev, "Published", False):
            # Determine viewer user id without enforcing auth redirect
            viewer_id = None
            try:
                from app.services.auth import get_user_id_from_request as _uid

                viewer_id = _uid(request, db)
            except Exception:
                viewer_id = None
            owner_id = getattr(ev, "UserID", None)
            if owner_id is not None and viewer_id is not None and owner_id == viewer_id:
                is_owner_preview = True
            else:
                return templates.TemplateResponse(request, "404.html", status_code=404)
    except Exception:
        return templates.TemplateResponse(request, "404.html", status_code=404)
    custom = db.query(EventCustomisation).filter(EventCustomisation.EventID == ev.EventID).first()
    theme = None
    try:
        if custom and getattr(custom, "ThemeID", None):
            theme = db.query(Theme).filter(Theme.ThemeID == custom.ThemeID).first()
    except Exception:
        theme = None
    canonical_url = None
    try:
        canonical_url = f"{str(request.base_url).rstrip('/')}/e/{code}"
    except Exception:
        canonical_url = None
    # Build inline CSS variables safely for theming
    share_theme_style = ""
    try:
        parts = []
        if custom:
            bg = getattr(custom, "BackgroundColour", None)
            txt = getattr(custom, "TextColour", None)
            btn = getattr(custom, "ButtonColour1", None)
            acc = getattr(custom, "AccentColour", None)
            if bg:
                parts.append(f"--bg: {bg};")
            if txt:
                parts.append(f"--txt: {txt};")
            if btn:
                parts.append(f"--share-btn: {btn};")
            if acc:
                parts.append(f"--share-accent: {acc};")
        share_theme_style = " ".join(parts)
    except Exception:
        share_theme_style = ""
    return templates.TemplateResponse(
        request,
        "share_event.html",
        context={
            "event": ev,
            "custom": custom,
            "theme": theme,
            "canonical_url": canonical_url,
            "share_theme_style": share_theme_style,
            "is_owner_preview": is_owner_preview,
        },
    )
