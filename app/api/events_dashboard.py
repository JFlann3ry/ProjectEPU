from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func as _func
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.models.event import Event, EventCustomisation, EventType, GuestSession, Theme
from app.services.auth import require_user
from app.services.thumbs import ensure_dashboard_cover_thumbnail
from db import get_db

router = APIRouter()


@router.get("/events", response_class=HTMLResponse)
async def events_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
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
            {getattr(r, "ThemeID", None) for r in ec_rows if getattr(r, "ThemeID", None)}
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
            dashboard_cover = None
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
                            cover = getattr(t, "CoverPhotoPath", None) or getattr(
                                t, "BackgroundImage", None
                            )
                    except Exception:
                        pass
            dashboard_cover = ensure_dashboard_cover_thumbnail(cover, width=480)
            setattr(e, "CoverPhotoPath", cover)
            setattr(e, "DashboardCoverPath", dashboard_cover or cover)
            setattr(e, "ShowCover", show_cover)
    except Exception:
        for e in events:
            setattr(e, "CoverPhotoPath", None)
            setattr(e, "DashboardCoverPath", None)
            setattr(e, "ShowCover", True)

    # If a cover points to an uploaded event media file, reuse the existing thumbnail endpoint.
    try:
        cover_pairs = []
        for e in events:
            cover = str(getattr(e, "CoverPhotoPath", "") or "")
            if not cover.startswith("/media/"):
                continue
            parts = cover.split("/")
            if len(parts) < 5:
                continue
            try:
                eid = int(parts[3])
            except Exception:
                continue
            filename = "/".join(parts[4:])
            cover_pairs.append((eid, filename))

        if cover_pairs:
            from app.models.event import FileMetadata

            event_ids = sorted({eid for eid, _filename in cover_pairs})
            file_names = sorted({filename for _eid, filename in cover_pairs})
            rows = (
                db.query(FileMetadata.FileMetadataID, FileMetadata.EventID, FileMetadata.FileName)
                .filter(FileMetadata.EventID.in_(event_ids), FileMetadata.FileName.in_(file_names))
                .all()
            )
            thumb_map = {
                (int(event_id), str(file_name)): f"/thumbs/{int(file_id)}.jpg?w=480"
                for file_id, event_id, file_name in rows
            }
            for e in events:
                cover = str(getattr(e, "CoverPhotoPath", "") or "")
                if not cover.startswith("/media/"):
                    continue
                parts = cover.split("/")
                if len(parts) < 5:
                    continue
                try:
                    eid = int(parts[3])
                except Exception:
                    continue
                filename = "/".join(parts[4:])
                thumb_url = thumb_map.get((eid, filename))
                if thumb_url:
                    setattr(e, "DashboardCoverPath", thumb_url)
    except Exception:
        pass

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

    # Annotate event tasks (purchase_extras, etc.) for current user
    try:
        from app.models.event import EventTask as ET

        event_ids = [e.EventID for e in events]
        rows = (
            db.query(ET)
            .filter(ET.EventID.in_(event_ids), ET.UserID == getattr(user, "UserID"))
            .all()
        )
        done_map = {(r.EventID, getattr(r, "Key", None)): True for r in rows}
        for e in events:
            e_purchase = bool(done_map.get((getattr(e, "EventID"), "purchase_extras"), False))
            setattr(e, "Task_purchase_extras", e_purchase)
    except Exception:
        for e in events:
            setattr(e, "Task_purchase_extras", False)

    # Plan badge
    plan, features = (None, {})
    try:
        from app.services.billing_utils import get_active_plan

        plan, features = get_active_plan(
            db,
            getattr(user, "UserID", 0),
            reconcile_pending=False,
        )
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
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
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
    request: Request,
    code: str,
    db: Session = Depends(get_db),
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
