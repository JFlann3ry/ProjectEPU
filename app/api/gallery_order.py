import hashlib

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.gallery_builders import _build_gallery_files
from app.models.event import Event
from app.models.photo_order import EventGalleryOrder
from app.services.auth import require_user
from db import get_db

router = APIRouter()


@router.get("/events/{event_id}/gallery/order", response_class=JSONResponse)
async def event_gallery_order(
    request: Request,
    event_id: int,
    show_deleted: bool = Query(False),
    favorites: bool = Query(False),
    album_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Return files for an event in canonical gallery order."""
    owned = (
        db.query(Event.EventID)
        .filter(Event.EventID == event_id, Event.UserID == user.UserID)
        .first()
    )
    if not owned:
        return JSONResponse({"ok": False, "error": "not_owned"}, status_code=404)

    files, _ = _build_gallery_files(
        db,
        user_id=user.UserID,
        event_id=event_id,
        type_filter=None,
        show_deleted=show_deleted,
        favorites_only=favorites,
        limit=0,
        offset=0,
        album_id=album_id,
    )

    try:
        order_ids = []
        try:
            from sqlalchemy import text

            sql = text("EXEC dbo.GetEventGalleryOrder :eid")
            res = db.execute(sql.bindparams(eid=event_id))
            rows = res.fetchall()
            order_ids = [int(r[0]) for r in rows] if rows else []
        except Exception:
            rows = (
                db.query(EventGalleryOrder.FileMetadataID)
                .filter(EventGalleryOrder.EventID == event_id)
                .order_by(EventGalleryOrder.Ordinal)
                .all()
            )
            order_ids = [int(r[0]) for r in rows] if rows else []
    except Exception:
        order_ids = []

    if order_ids:
        by_id = {int(f["id"]): f for f in files}
        ordered = []
        for fid in order_ids:
            if fid in by_id:
                ordered.append(by_id.pop(fid))
        if by_id:
            for f in files:
                if int(f["id"]) in by_id:
                    ordered.append(by_id.pop(int(f["id"])))
        files = ordered

    try:
        if files:
            file_ids = []
            for f in files:
                try:
                    v = f.get("id")
                    if v is None:
                        continue
                    file_ids.append(int(v))
                except Exception:
                    continue
            if file_ids:
                rows = (
                    db.query(
                        EventGalleryOrder.FileMetadataID,
                        EventGalleryOrder.Ordinal,
                    )
                    .filter(
                        EventGalleryOrder.EventID == event_id,
                        EventGalleryOrder.FileMetadataID.in_(file_ids),
                    )
                    .all()
                )
                ord_map = {}
                for r in rows or []:
                    try:
                        fid = int(r[0])
                        ordv = getattr(r, "Ordinal", None)
                        if ordv is None:
                            try:
                                ordv = int(r[1])
                            except Exception:
                                ordv = None
                        if ordv is not None:
                            ord_map[fid] = int(ordv)
                    except Exception:
                        continue
                for f in files:
                    try:
                        fidv = f.get("id")
                        if fidv is None:
                            continue
                        fid = int(fidv)
                        if fid in ord_map:
                            f["ordinal"] = ord_map[fid]
                    except Exception:
                        continue
    except Exception:
        pass

    try:
        et_src = ",".join(str(int(f.get("id", ""))) for f in files)
        etag = hashlib.sha256(et_src.encode("utf-8")).hexdigest()
    except Exception:
        etag = None

    try:
        inm = request.headers.get("if-none-match") or request.headers.get("If-None-Match")
        if inm and etag and inm.strip('"') == etag:
            headers = {"ETag": '"%s"' % etag}
            return JSONResponse({"ok": True, "files": []}, status_code=304, headers=headers)
    except Exception:
        pass

    last_modified = None
    try:
        if order_ids:
            last_row = (
                db.query(EventGalleryOrder.UpdatedAt)
                .filter(EventGalleryOrder.EventID == event_id)
                .order_by(EventGalleryOrder.UpdatedAt.desc())
                .first()
            )
            if last_row and getattr(last_row, "UpdatedAt", None):
                last_modified = last_row.UpdatedAt
    except Exception:
        last_modified = None

    headers = {"Cache-Control": "private, max-age=30"}
    if etag:
        headers["ETag"] = '"%s"' % etag
    if last_modified:
        try:
            from email.utils import format_datetime

            headers["Last-Modified"] = format_datetime(last_modified)
        except Exception:
            pass

    return JSONResponse({"ok": True, "files": files}, headers=headers)
