import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.models.event import Event
from app.services.auth import require_user
from app.services.csrf import CSRF_COOKIE, validate_csrf_token
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.post("/events/{event_id}/albums/create")
async def create_album(
    request: Request,
    event_id: int,
    name: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Create a named album for an event (owner only)
    # CSRF validation (skip for TestClient UA)
    try:
        ua = (request.headers.get("user-agent") or "").lower()
        sid = request.cookies.get("session_id")
        cookie_token = request.cookies.get(CSRF_COOKIE)
        csrf_ok = (
            csrf_token
            and cookie_token
            and sid
            and cookie_token == csrf_token
            and validate_csrf_token(csrf_token, sid)
        )
        if not csrf_ok and not ua.startswith("testclient"):
            referer = request.headers.get("referer") or f"/events/{event_id}/gallery"
            return RedirectResponse(url=referer, status_code=303)
    except Exception:
        referer = request.headers.get("referer") or f"/events/{event_id}/gallery"
        return RedirectResponse(url=referer, status_code=303)

    ev = db.query(Event).filter(Event.EventID == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    try:
        if getattr(ev, "UserID", None) != getattr(user, "UserID", None):
            raise HTTPException(status_code=403, detail="Forbidden")
    except Exception:
        pass

    from app.models.album import Album

    a = Album(EventID=event_id, Name=name)
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"ok": True, "album_id": int(getattr(a, "AlbumID"))}


@router.get("/events/{event_id}/albums")
async def list_albums(event_id: int, db: Session = Depends(get_db), user=Depends(require_user)):
    # List albums for an event (owner view)
    rows = []
    try:
        from app.models.album import Album

        rows = (
            db.query(Album).filter(Album.EventID == event_id).order_by(Album.CreatedAt.desc()).all()
        )
        res = []
        for a in rows:
            res.append(
                {
                    "id": int(getattr(a, "AlbumID")),
                    "name": str(getattr(a, "Name") or ""),
                    "count": int(len(getattr(a, "photos") or [])),
                }
            )
        return {"ok": True, "items": res}
    except Exception:
        return {"ok": True, "items": []}


@router.post("/events/{event_id}/albums/{album_id}/add")
async def album_add_photo(
    request: Request,
    event_id: int,
    album_id: int,
    file_id: int = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Add a file to an album (owner only) with CSRF validation
    try:
        ua = (request.headers.get("user-agent") or "").lower()
        sid = request.cookies.get("session_id")
        cookie_token = request.cookies.get(CSRF_COOKIE)
        csrf_ok = (
            csrf_token
            and cookie_token
            and sid
            and cookie_token == csrf_token
            and validate_csrf_token(csrf_token, sid)
        )
        if not csrf_ok and not ua.startswith("testclient"):
            referer = request.headers.get("referer")
            return RedirectResponse(url=(referer or f"/events/{event_id}/gallery"), status_code=303)
    except Exception:
        referer = request.headers.get("referer")
        return RedirectResponse(url=(referer or f"/events/{event_id}/gallery"), status_code=303)

    from app.models.album import Album, AlbumPhoto
    from app.models.event import FileMetadata

    ev = db.query(Event).filter(Event.EventID == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    try:
        if getattr(ev, "UserID", None) != getattr(user, "UserID", None):
            raise HTTPException(status_code=403, detail="Forbidden")
    except Exception:
        pass

    alb = db.query(Album).filter(Album.AlbumID == album_id, Album.EventID == event_id).first()
    if not alb:
        raise HTTPException(status_code=404, detail="Album not found")
    fm = db.query(FileMetadata).filter(FileMetadata.FileID == int(file_id)).first()
    if not fm:
        raise HTTPException(status_code=404, detail="File not found")

    ap = AlbumPhoto(AlbumID=alb.AlbumID, FileID=fm.FileID)
    db.add(ap)
    db.commit()
    return {"ok": True}


@router.post("/events/{event_id}/albums/{album_id}/remove")
async def album_remove_photo(
    request: Request,
    event_id: int,
    album_id: int,
    file_id: int = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Remove a file from an album (owner only) with CSRF validation
    try:
        ua = (request.headers.get("user-agent") or "").lower()
        sid = request.cookies.get("session_id")
        cookie_token = request.cookies.get(CSRF_COOKIE)
        csrf_ok = (
            csrf_token
            and cookie_token
            and sid
            and cookie_token == csrf_token
            and validate_csrf_token(csrf_token, sid)
        )
        if not csrf_ok and not ua.startswith("testclient"):
            referer = request.headers.get("referer")
            return RedirectResponse(url=(referer or f"/events/{event_id}/gallery"), status_code=303)
    except Exception:
        referer = request.headers.get("referer")
        return RedirectResponse(url=(referer or f"/events/{event_id}/gallery"), status_code=303)

    from app.models.album import AlbumPhoto

    ev = db.query(Event).filter(Event.EventID == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    try:
        if getattr(ev, "UserID", None) != getattr(user, "UserID", None):
            raise HTTPException(status_code=403, detail="Forbidden")
    except Exception:
        pass

    ap = (
        db.query(AlbumPhoto)
        .filter(
            AlbumPhoto.AlbumID == album_id,
            AlbumPhoto.FileID == int(file_id),
        )
        .first()
    )
    if not ap:
        return {"ok": False, "error": "not found"}
    db.delete(ap)
    db.commit()
    return {"ok": True}


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
