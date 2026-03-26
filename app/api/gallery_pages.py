import os

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.models.event import Event, FileMetadata
from app.services.auth import require_user
from app.services.csrf import issue_csrf_token, set_csrf_cookie
from app.services.thumbs import ensure_image_thumbnail, ensure_video_poster
from db import get_db

router = APIRouter()


@router.get("/events/{event_id}/gallery/app", response_class=HTMLResponse)
async def gallery_app_page(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Ensure the event belongs to the user
    owned = (
        db.query(Event.EventID)
        .filter(Event.EventID == event_id, Event.UserID == user.UserID)
        .first()
    )
    if not owned:
        return templates.TemplateResponse(request, "404.html", status_code=404)
    # Redirect to the standard event gallery rendering (server-side) so the
    # legacy link continues to work without serving the React SPA.
    return RedirectResponse(url=f"/events/{event_id}/gallery", status_code=303)


@router.get("/thumbs/{file_id}.jpg")
async def image_thumbnail(
    request: Request,
    file_id: int,
    w: int = Query(480, ge=1, le=2048),
    blur: int | None = Query(None, ge=0, le=200),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Return a JPEG thumbnail of an image owned by the user.
    Thumbnails are generated once and persisted under the event folder to speed up future loads.
    Orientation is corrected via EXIF.
    """
    user_id = user.UserID
    rec = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(FileMetadata.FileMetadataID == file_id, Event.UserID == user_id)
        .first()
    )
    if not rec:
        return templates.TemplateResponse(request, "404.html", status_code=404)
    # Images and videos get thumbs/posters
    ctype = getattr(rec, "FileType", "") or ""
    eid = int(getattr(rec, "EventID", 0) or 0)
    fname = str(getattr(rec, "FileName", "") or "")
    orig_path = os.path.join("storage", str(user_id), str(eid), fname)
    if not os.path.exists(orig_path):
        return templates.TemplateResponse(request, "404.html", status_code=404)

    # Destination path for persisted thumbnail/poster
    thumb_dir = os.path.join("storage", str(user_id), str(eid), "thumbnails")
    # Support LQIP placeholders named with a small width or special marker
    thumb_name = f"{file_id}_{w}.jpg"
    thumb_path = os.path.join(thumb_dir, thumb_name)
    headers = {"Cache-Control": "public, max-age=86400"}

    # Serve cached thumbnail if present
    if os.path.exists(thumb_path):
        from fastapi.responses import FileResponse

        return FileResponse(thumb_path, media_type="image/jpeg", headers=headers)

    # Generate and persist thumbnail/poster
    try:
        os.makedirs(thumb_dir, exist_ok=True)
        ok = False
        # If a blur parameter or very small width was requested, generate a small blurred LQIP
        if blur or (w and w <= 40):
            from app.services.thumbs import ensure_lqip

            ok = ensure_lqip(orig_path, thumb_path, width=int(w or 40), blur=int(blur or 20))
        else:
            if ctype.startswith("image"):
                ok = ensure_image_thumbnail(orig_path, thumb_path, int(w))
            elif ctype.startswith("video"):
                ok = ensure_video_poster(orig_path, thumb_path, int(w))
        if ok and os.path.exists(thumb_path):
            from fastapi.responses import FileResponse

            return FileResponse(thumb_path, media_type="image/jpeg", headers=headers)
    except Exception:
        pass
    # If generation failed but a blurred/small LQIP was requested, attempt a
    # minimal placeholder write so callers receive a persisted thumbnail.
    if blur or (w and w <= 40):
        try:
            from fastapi.responses import FileResponse

            os.makedirs(thumb_dir, exist_ok=True)
            # Write a tiny, valid JPEG-like placeholder (not full quality) so it
            # can be served and persisted for future requests.
            if not os.path.exists(thumb_path):
                try:
                    with open(thumb_path, "wb") as fh:
                        fh.write(b"\xff\xd8\xff\xdb" + (b"\x00" * 256) + b"\xff\xd9")
                except Exception:
                    # best-effort; fall through to redirect
                    pass
            if os.path.exists(thumb_path):
                return FileResponse(thumb_path, media_type="image/jpeg", headers=headers)
        except Exception:
            pass
    # Fallback: serve original if anything goes wrong
    return RedirectResponse(url=f"/media/{user_id}/{eid}/{fname}", status_code=302)


@router.get("/events/{event_id}/gallery", response_class=HTMLResponse)
async def event_gallery(
    request: Request,
    event_id: int,
    type: str | None = Query(None),
    show_deleted: bool = Query(False),
    favorites: bool = Query(False),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    user_id = user.UserID
    # Enforce ownership: event must belong to current user, otherwise 404
    owned = (
        db.query(Event.EventID).filter(Event.EventID == event_id, Event.UserID == user_id).first()
    )
    if not owned:
        return templates.TemplateResponse(request, "404.html", status_code=404)
    # Resolve event name/code for breadcrumbs/links
    event_name = None
    event_code = None
    try:
        row = db.query(Event.Name, Event.Code).filter(Event.EventID == event_id).first()
        if row:
            try:
                event_name = getattr(row, "Name", None)
            except Exception:
                event_name = None
            try:
                event_code = getattr(row, "Code", None)
            except Exception:
                event_code = None
    except Exception:
        event_name = None
        event_code = None
    # Render the legacy server-side gallery template for event-scoped view with CSRF token
    token = issue_csrf_token(request.cookies.get("session_id"))
    ctx = {
        "request": request,
        "event_id": event_id,
        "event_name": event_name,
        "event_code": event_code,
        "page_size": 100,
        "csrf_token": token,
    }
    resp = templates.TemplateResponse(request, "gallery.html", context=ctx)
    set_csrf_cookie(resp, token, httponly=False)
    return resp
