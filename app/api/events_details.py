from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func as _func
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.addons import AddonCatalog
from app.models.event import Event, EventCustomisation, EventType, FileMetadata
from app.services.auth import require_user
from db import get_db

router = APIRouter()


@router.get("/events/code/{code}", response_class=HTMLResponse)
async def owner_event_details_by_code(
    request: Request,
    code: str,
    db: Session = Depends(get_db),
    user=Depends(require_user),
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
    custom = db.query(EventCustomisation).filter(EventCustomisation.EventID == event_id).first()
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
            base.filter(FileMetadata.FileType.like("image%")).with_entities(_func.count()).scalar()
            or 0
        )
        upload_stats["videos"] = int(
            base.filter(FileMetadata.FileType.like("video%")).with_entities(_func.count()).scalar()
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
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
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
            base.filter(FileMetadata.FileType.like("image%")).with_entities(_func.count()).scalar()
            or 0
        )
        upload_stats["videos"] = int(
            base.filter(FileMetadata.FileType.like("video%")).with_entities(_func.count()).scalar()
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
