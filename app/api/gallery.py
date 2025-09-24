import hashlib
import io
import os
import zipfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from sqlalchemy import case
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.album import Album, AlbumPhoto
from app.models.event import Event, FavoriteFile, FileMetadata
from app.models.photo_order import EventGalleryOrder
from app.services.auth import require_user
from app.services.csrf import validate_csrf_token
from app.services.thumbs import (
    cleanup_thumbnails,
    ensure_image_thumbnail,
    ensure_video_poster,
)
from db import get_db

router = APIRouter()

# Signed cookie name for gallery scoping (stores the selected EventID)
GALLERY_COOKIE = "gallery_scope"

# Cache DB feature detection for optional columns
_HAS_DELETED_AT: Optional[bool] = None


def _has_deleted_at(db: Session) -> bool:
    global _HAS_DELETED_AT
    if _HAS_DELETED_AT is not None:
        return _HAS_DELETED_AT
    try:
        bind = getattr(db, "bind", None)
        if bind is None:
            _HAS_DELETED_AT = False
            return _HAS_DELETED_AT
        insp = sa_inspect(bind)
        cols = [c.get("name") for c in insp.get_columns("FileMetadata")]
        _HAS_DELETED_AT = any((n == "DeletedAt" for n in cols))
    except Exception:
        _HAS_DELETED_AT = False
    return _HAS_DELETED_AT


def _sign_scope(value: str) -> str:
    import hashlib
    import hmac

    key = (settings.SECRET_KEY or "change-me").encode("utf-8")
    sig = hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{value}:{sig}"


def _verify_scope(value: str) -> Optional[str]:
    try:
        raw, sig = value.rsplit(":", 1)
    except ValueError:
        return None
    import hashlib
    import hmac

    key = (settings.SECRET_KEY or "change-me").encode("utf-8")
    expected = hmac.new(key, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, expected):
        return raw
    return None


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
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=f"/events/{event_id}/gallery", status_code=303)


def _build_gallery_files(
    db: Session,
    user_id: int,
    event_id: int | None,
    type_filter: str | None,
    show_deleted: bool,
    favorites_only: bool = False,
    limit: int | None = None,
    offset: int | None = None,
    album_id: int | None = None,
) -> tuple[list[dict], bool]:

    # Scope to user (and optionally an event)
    event_query = db.query(Event).filter(Event.UserID == user_id)
    if event_id is not None:
        event_query = event_query.filter(Event.EventID == event_id)
    event_ids = [e.EventID for e in event_query.all()]
    if not event_ids:
        return [], False
    # Build explicit column list to avoid selecting optional columns on legacy DBs
    has_del_at = _has_deleted_at(db)
    select_cols = [
        FileMetadata.FileMetadataID,
        FileMetadata.EventID,
        FileMetadata.FileName,
        FileMetadata.FileType,
        FileMetadata.CapturedDateTime,
        FileMetadata.UploadDate,
        FileMetadata.Deleted,
    ]
    if has_del_at:
        try:
            select_cols.append(FileMetadata.DeletedAt)
        except Exception:
            has_del_at = False
    q = db.query(*select_cols).filter(FileMetadata.EventID.in_(event_ids))
    # If album_id provided, restrict to files belonging to that album
    if album_id is not None:
        try:
            # Ensure album belongs to one of the scoped events
            alb = db.query(Album).filter(Album.AlbumID == album_id).first()
            a_eid = None
            if alb is not None:
                raw_eid = getattr(alb, "EventID", None)
                try:
                    a_eid = int(raw_eid) if raw_eid is not None else None
                except Exception:
                    a_eid = None
            if not alb or a_eid not in event_ids:
                return [], False
            # Get FileIDs for album
            rows_fp = db.query(AlbumPhoto.FileID).filter(AlbumPhoto.AlbumID == album_id).all()
            file_ids = set()
            for r in rows_fp or []:
                try:
                    file_ids.add(int(r[0]))
                except Exception:
                    continue
            if not file_ids:
                return [], False
            q = q.filter(FileMetadata.FileMetadataID.in_(file_ids))
        except Exception:
            return [], False
    # Deleted filter: when show_deleted is true, ONLY show deleted files; otherwise only non-deleted
    if show_deleted:
        q = q.filter(FileMetadata.Deleted)
    else:
        q = q.filter(~FileMetadata.Deleted)
    # Type filter
    if type_filter in ("image", "video"):
        prefix = f"{type_filter}/"
        q = q.filter(FileMetadata.FileType.like(prefix + "%"))

    # Favorites only filter
    fav_ids = set()
    if favorites_only:
        fav_rows = (
            db.query(FavoriteFile.FileMetadataID).filter(FavoriteFile.UserID == user_id).all()
        )
        fav_ids = set(int(r[0]) for r in fav_rows)
        if not fav_ids:
            return [], False
        q = q.filter(FileMetadata.FileMetadataID.in_(fav_ids))

    # Sort by CapturedDateTime asc (chronological).
    # Put NULL captured times last, then by UploadDate asc.
    q = q.order_by(
        case((FileMetadata.CapturedDateTime.is_(None), 1), else_=0),
        FileMetadata.CapturedDateTime.asc(),
        FileMetadata.UploadDate.asc(),
    )
    files: list[dict] = []
    # Preload favorites set for flag
    if not favorites_only:
        fav_rows2 = (
            db.query(FavoriteFile.FileMetadataID).filter(FavoriteFile.UserID == user_id).all()
        )
        fav_ids = set(int(r[0]) for r in fav_rows2)

    # Attempt to prefer EventGalleryOrder when scoped to a single event.
    order_ids: list[int] = []
    if event_id is not None:
        try:
            from sqlalchemy import text

            # Try calling dbo.GetEventGalleryOrder(@EventID) (SQL Server stored proc)
            sql = text("EXEC dbo.GetEventGalleryOrder :eid")
            res = db.execute(sql.bindparams(eid=event_id))
            rows_sp = res.fetchall()
            order_ids = [int(r[0]) for r in rows_sp] if rows_sp else []
        except Exception:
            try:
                rows_o = (
                    db.query(EventGalleryOrder.FileMetadataID)
                    .filter(EventGalleryOrder.EventID == event_id)
                    .order_by(EventGalleryOrder.Ordinal)
                    .all()
                )
                order_ids = [int(r[0]) for r in rows_o] if rows_o else []
            except Exception:
                order_ids = []

    # If we have explicit ordinal ordering, build the full ordered row list in Python
    # (ordered rows first, then any remaining files in chronological order), then
    # apply pagination in Python so offset/limit reflect the canonical order.
    rows: list = []
    has_more = False
    if order_ids:
        try:
            all_rows = list(q)
            # map id->row
            idx_id = 0
            by_id = {int(r[idx_id]): r for r in all_rows}
            ordered_rows: list = []
            for fid in order_ids:
                if fid in by_id:
                    ordered_rows.append(by_id.pop(fid))
            # append remaining rows in the chronological order provided by `q`
            if by_id:
                for r in all_rows:
                    try:
                        rid = int(r[idx_id])
                    except Exception:
                        continue
                    if rid in by_id:
                        ordered_rows.append(by_id.pop(rid))
            # Apply offset/limit in Python
            start = int(offset or 0)
            if limit and int(limit) > 0:
                lim = int(limit)
                slice_rows = ordered_rows[start : start + lim]
                has_more = len(ordered_rows) > (start + lim)
            else:
                slice_rows = ordered_rows[start:]
                has_more = False
            rows = slice_rows
        except Exception:
            # Fall back to DB pagination when anything unexpected happens
            rows = []
            has_more = False

    if not order_ids:
        # Pagination: fetch one extra to know if more remain
        q2 = q
        if offset:
            try:
                q2 = q2.offset(int(offset))
            except Exception:
                pass
        fetch_limit = None
        if limit and limit > 0:
            try:
                fetch_limit = int(limit) + 1
                q2 = q2.limit(fetch_limit)
            except Exception:
                pass

        rows = list(q2)
        has_more = False
        if fetch_limit is not None and len(rows) > (fetch_limit - 1):
            has_more = True
            rows = rows[: (fetch_limit - 1)]

    # Indexes into row tuple
    idx_id = 0
    idx_event = 1
    idx_name = 2
    idx_filetype = 3
    idx_captured = 4
    idx_deleted = 6
    idx_deleted_at = 7 if has_del_at else None

    for row in rows:
        ftype = "other"
        ctype = (row[idx_filetype] or "") if row is not None else ""
        if ctype.startswith("image"):
            ftype = "image"
        elif ctype.startswith("video"):
            ftype = "video"
        thumb_url = None
        if ftype in ("image", "video"):
            # Use id-based thumb/poster endpoint for caching; prefer 720 for grid
            thumb_url = f"/thumbs/{row[idx_id]}.jpg?w=720"
        # Build srcset candidates
        srcset = None
        if ftype == "image":
            srcset = ", ".join(
                [
                    f"/thumbs/{row[idx_id]}.jpg?w=480 480w",
                    f"/thumbs/{row[idx_id]}.jpg?w=720 720w",
                    f"/thumbs/{row[idx_id]}.jpg?w=960 960w",
                    f"/thumbs/{row[idx_id]}.jpg?w=1440 1440w",
                ]
            )
        # Deletion countdown
        deleted_flag = bool(row[idx_deleted])
        deleted_at = (row[idx_deleted_at] if (has_del_at and idx_deleted_at is not None) else None)
        days_left = None
        if deleted_flag:
            if has_del_at and deleted_at is not None:
                try:
                    delta_days = (datetime.now(timezone.utc) - deleted_at).days
                    days_left = max(0, 30 - max(0, delta_days))
                except Exception:
                    days_left = None
            else:
                # In deleted view without DeletedAt column, provide a grouping bucket for "unknown"
                if show_deleted:
                    days_left = 9999  # sentinel for unknown countdown

        days_label = None
        if deleted_flag:
            try:
                if isinstance(days_left, int):
                    if days_left >= 9999:
                        days_label = "Deletion date unknown"
                    elif days_left <= 0:
                        days_label = "Deleting soon"
                    elif days_left == 1:
                        days_label = "1 day left"
                    else:
                        days_label = (
                            f"{days_left} days left"
                        )
            except Exception:
                days_label = None
        # precompute thumbnail id-based URLs to keep lines short for linters
        thumb_480 = (
            f"/thumbs/{row[idx_id]}.jpg?w=480" if ftype in ("image", "video") else None
        )
        thumb_720 = (
            f"/thumbs/{row[idx_id]}.jpg?w=720" if ftype in ("image", "video") else None
        )
        thumb_960 = (
            f"/thumbs/{row[idx_id]}.jpg?w=960" if ftype in ("image", "video") else None
        )
        thumb_1440 = (
            f"/thumbs/{row[idx_id]}.jpg?w=1440" if ftype in ("image", "video") else None
        )

        files.append(
            {
                "id": row[idx_id],
                "event_id": row[idx_event],
                "type": ftype,
                "url": f"/storage/{user_id}/{row[idx_event]}/{row[idx_name]}",
                "thumb_url": thumb_url,
                "thumbnail_480": thumb_480,
                "thumbnail_720": thumb_720,
                "thumbnail_960": thumb_960,
                "thumbnail_1440": thumb_1440,
                "srcset": srcset,
                "name": row[idx_name],
                "datetime": (
                    row[idx_captured].isoformat() if row[idx_captured] else None
                ),
                "deleted": deleted_flag,
                "deleted_at": (deleted_at.isoformat() if deleted_at else None),
                "days_left": days_left,
                "days_label": days_label,
                "favorite": (row[idx_id] in fav_ids),
            }
        )
    return files, has_more


@router.get("/gallery", response_class=HTMLResponse)
async def user_gallery(
    request: Request,
    type: str | None = Query(None),
    show_deleted: bool = Query(False),
    favorites: bool = Query(False),
    album_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Basic request/user scope initialization
    user_id = user.UserID
    selected_event_id: int | None = None

    # Restore scoped event from signed cookie when present
    scope_cookie = request.cookies.get(GALLERY_COOKIE)
    if scope_cookie:
        raw = _verify_scope(scope_cookie) or None
        if raw:
            try:
                eid = int(raw)
            except Exception:
                eid = None
            if eid is not None:
                try:
                    owned = (
                        db.query(Event.EventID, Event.Name)
                        .filter(Event.EventID == eid, Event.UserID == user_id)
                        .first()
                    )
                    if owned:
                        selected_event_id = eid
                except Exception:
                    # ignore DB lookup failures and leave selection empty
                    pass
    PAGE_SIZE = 60
    # Determine if any deleted files exist within the scoped events (ignore result)
    try:
        qdel = (
            db.query(FileMetadata.FileMetadataID)
            .join(Event, Event.EventID == FileMetadata.EventID)
            .filter(Event.UserID == user_id, FileMetadata.Deleted)
        )
        if selected_event_id is not None:
            qdel = qdel.filter(Event.EventID == selected_event_id)
        _ = bool(qdel.first())
    except Exception:
        pass

    # Compute counts for filter pills based on current scope and toggles
    def _get_event_ids() -> list[int]:
        q = db.query(Event.EventID).filter(Event.UserID == user_id)
        if selected_event_id is not None:
            q = q.filter(Event.EventID == selected_event_id)
        try:
            return [int(r[0]) for r in q.all()]
        except Exception:
            return []

    def _count_base(event_ids: list[int]):
        return db.query(FileMetadata).filter(FileMetadata.EventID.in_(event_ids))

    counts = {"all": 0, "images": 0, "videos": 0, "favorites": 0, "deleted": 0}
    try:
        eids = _get_event_ids()
        if eids:
            # Base for current favorites toggle
            base = _count_base(eids)
            if favorites:
                base = (
                    base.join(
                        FavoriteFile,
                        FavoriteFile.FileMetadataID == FileMetadata.FileMetadataID,
                    ).filter(FavoriteFile.UserID == user_id)
                )
            # Apply current deleted mode for All/Images/Videos counts
            cur_del = show_deleted
            base_cur = base.filter(FileMetadata.Deleted == cur_del)
            counts["all"] = base_cur.count()
            counts["images"] = base_cur.filter(FileMetadata.FileType.like("image/%")).count()
            counts["videos"] = base_cur.filter(FileMetadata.FileType.like("video/%")).count()

            # Favorites count: if Favorites toggle is ON
            # (preserve current type and deleted mode)
            fav_q = _count_base(eids)
            # preserve deleted mode
            fav_q = fav_q.filter(FileMetadata.Deleted == cur_del)
            # preserve current type filter if any
            if type in ("image", "video"):
                fav_q = fav_q.filter(FileMetadata.FileType.like(f"{type}/%"))
            fav_q = (
                fav_q.join(
                    FavoriteFile,
                    FavoriteFile.FileMetadataID == FileMetadata.FileMetadataID,
                ).filter(FavoriteFile.UserID == user_id)
            )
            counts["favorites"] = fav_q.count()

            # Deleted count: if Deleted mode is ON
            # (preserve current favorites and type filters)
            del_q = _count_base(eids)
            # preserve current favorites toggle
            if favorites:
                del_q = (
                    del_q.join(
                        FavoriteFile,
                        FavoriteFile.FileMetadataID == FileMetadata.FileMetadataID,
                    ).filter(FavoriteFile.UserID == user_id)
                )
            # preserve current type filter
            if type in ("image", "video"):
                del_q = del_q.filter(FileMetadata.FileType.like(f"{type}/%"))
            del_q = del_q.filter(FileMetadata.Deleted == True)  # noqa: E712
            counts["deleted"] = del_q.count()
    except Exception:
        pass

    files, has_more = _build_gallery_files(
        db,
        user_id=user_id,
        event_id=selected_event_id,
        type_filter=type,
        show_deleted=show_deleted,
        favorites_only=favorites,
        limit=PAGE_SIZE,
        offset=0,
        album_id=album_id,
    )
    # Attach ordinal values from EventGalleryOrder for server-rendered files when possible
    try:
        if selected_event_id is not None and files:
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
                        EventGalleryOrder.EventID == selected_event_id,
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
                try:
                    if any((isinstance(f.get("ordinal"), int) for f in files)):
                        def _ord_key(item: dict) -> int:
                            v = item.get("ordinal")
                            try:
                                return int(v) if v is not None else 2 ** 60
                            except Exception:
                                return 2 ** 60

                        files.sort(key=_ord_key)
                except Exception:
                    pass
    except Exception:
        pass
    # To preserve compatibility with old links, serve the React single-page
    # app here and pass a sensible event_id: prefer the scoped event, else the
    # user's first event id, else 0. This makes old /gallery links load the
    # modern React app without changing other templates.
    try:
        if selected_event_id is None:
            first_evt = (
                db.query(Event.EventID)
                .filter(Event.UserID == user_id)
                .order_by(Event.EventID)
                .first()
            )
            if first_evt:
                try:
                    selected_event_id = int(getattr(first_evt, "EventID"))
                except Exception:
                    selected_event_id = None
    except Exception:
        # ignore DB errors and fall back to 0
        selected_event_id = selected_event_id or None

    # Render the server-side gallery template (legacy behavior)
    ctx = {
        "request": request,
        "event_id": selected_event_id or 0,
        "files": files,
        "next_offset": None,
        "page_size": PAGE_SIZE,
        "filters": {"type": type, "show_deleted": show_deleted, "favorites": favorites},
        "counts": counts,
        "has_deleted": bool(_has_deleted_at(db)),
    }
    return templates.TemplateResponse(request, "gallery.html", context=ctx)


@router.get("/gallery/data", response_class=JSONResponse)
async def gallery_data(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(60, ge=1, le=200),
    type: str | None = Query(None),
    show_deleted: bool = Query(False),
    favorites: bool = Query(False),
    album_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    user_id = user.UserID
    # Use the same selected event from cookie
    selected_event_id: int | None = None
    scope_cookie = request.cookies.get(GALLERY_COOKIE)
    if scope_cookie:
        raw = _verify_scope(scope_cookie) or None
        if raw:
            try:
                eid = int(raw)
            except Exception:
                eid = None
            if eid is not None:
                owned = (
                    db.query(Event.EventID)
                    .filter(Event.EventID == eid, Event.UserID == user_id)
                    .first()
                )
                if owned:
                    selected_event_id = eid
    files, has_more = _build_gallery_files(
        db,
        user_id=user_id,
        event_id=selected_event_id,
        type_filter=type,
        show_deleted=show_deleted,
        favorites_only=favorites,
    limit=limit,
    offset=offset,
    album_id=album_id,
    )
    # Attach ordinal values from EventGalleryOrder when available for the scoped event
    try:
        if selected_event_id is not None and files:
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
                        EventGalleryOrder.EventID == selected_event_id,
                        EventGalleryOrder.FileMetadataID.in_(file_ids),
                    )
                    .all()
                )
                ord_map = {}
                for r in rows or []:
                    try:
                        fid = int(r[0])
                        # r may be a Row object; attempt attribute then index
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
    next_offset = (offset + len(files)) if has_more else None
    return JSONResponse({"ok": True, "files": files, "next_offset": next_offset})


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
    """Return files for an event in the canonical gallery order.

    Preference order:
    1. If EventGalleryOrder rows exist for the event, use that Ordinal ordering.
    2. Otherwise, fall back to the capture/upload chronological ordering produced by
       _build_gallery_files (CapturedDateTime asc, NULLs last, then UploadDate asc).
    """
    # Ensure event belongs to user
    owned = (
        db.query(Event.EventID)
        .filter(Event.EventID == event_id, Event.UserID == user.UserID)
        .first()
    )
    if not owned:
        return JSONResponse({"ok": False, "error": "not_owned"}, status_code=404)

    # Use the existing builder to get the canonical list (fallback)
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
        # Prefer stored procedure if available (SQL Server). This keeps ordering logic
        # close to the DB and avoids extra ORM work for large galleries.
        try:
            from sqlalchemy import text

            # Try calling dbo.GetEventGalleryOrder(@EventID)
            sql = text("EXEC dbo.GetEventGalleryOrder :eid")
            res = db.execute(sql.bindparams(eid=event_id))
            rows = res.fetchall()
            order_ids = [int(r[0]) for r in rows] if rows else []
        except Exception:
            # Fallback to ORM query if SP call failed / not available
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
        # append any remaining files not present in EventGalleryOrder in their original order
        if by_id:
            for f in files:
                if int(f["id"]) in by_id:
                    ordered.append(by_id.pop(int(f["id"])))
        files = ordered

    # Attach ordinal values to each file object when EventGalleryOrder rows exist
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

    # Build a simple ETag based on file ids + last-order hash
    try:
        et_src = ",".join(str(int(f.get("id", ""))) for f in files)
        etag = hashlib.sha256(et_src.encode("utf-8")).hexdigest()
    except Exception:
        etag = None

    # If client provided If-None-Match matching our ETag, return 304
    try:
        inm = request.headers.get("if-none-match") or request.headers.get("If-None-Match")
        if inm and etag and inm.strip('"') == etag:
            headers = {"ETag": '"%s"' % etag}
            return JSONResponse({"ok": True, "files": []}, status_code=304, headers=headers)
    except Exception:
        pass

    # Attempt to set Last-Modified based on EventGalleryOrder updated timestamp when available
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
            # Format as RFC1123 GMT
            from email.utils import format_datetime

            headers["Last-Modified"] = format_datetime(last_modified)
        except Exception:
            pass

    return JSONResponse({"ok": True, "files": files}, headers=headers)


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
    return RedirectResponse(url=f"/storage/{user_id}/{eid}/{fname}", status_code=302)


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
        db.query(Event.EventID)
        .filter(Event.EventID == event_id, Event.UserID == user_id)
        .first()
    )
    if not owned:
        return templates.TemplateResponse(request, "404.html", status_code=404)
    # Render the legacy server-side gallery template for event-scoped view
    ctx = {"request": request, "event_id": event_id, "page_size": 60}
    return templates.TemplateResponse(request, "gallery.html", context=ctx)


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


def _get_user_file_records(db: Session, user_id: int, file_ids: list[int]):
    from app.models.event import Event, FileMetadata

    if not file_ids:
        return []
    # Ensure files belong to user's events
    q = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == user_id, FileMetadata.FileMetadataID.in_(file_ids))
    )
    return q.all()


@router.post("/gallery/actions/delete")
async def gallery_delete(
    request: Request,
    file_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    files = _get_user_file_records(db, user.UserID, file_ids)
    has_del_at = _has_deleted_at(db)
    for f in files:
        setattr(f, "Deleted", True)
        try:
            # Set soft-delete timestamp if not already set
            if has_del_at and getattr(f, "DeletedAt", None) is None:
                try:
                    setattr(
                        f,
                        "DeletedAt",
                        datetime.now(timezone.utc),
                    )
                except Exception:
                    pass
        except Exception:
            pass
    if files:
        db.commit()
    referer = request.headers.get("referer") or "/gallery"
    return RedirectResponse(url=referer, status_code=303)


@router.post("/gallery/actions/restore")
async def gallery_restore(
    request: Request,
    file_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    files = _get_user_file_records(db, user.UserID, file_ids)
    has_del_at = _has_deleted_at(db)
    for f in files:
        setattr(f, "Deleted", False)
        try:
            if has_del_at:
                setattr(f, "DeletedAt", None)
        except Exception:
            pass
    if files:
        db.commit()
    # If no deleted files remain in the current scope, return to default gallery view
    # Determine selected event scope from cookie (same behavior as GET /gallery)
    selected_event_id: int | None = None
    try:
        scope_cookie = request.cookies.get(GALLERY_COOKIE)
        if scope_cookie:
            raw = _verify_scope(scope_cookie) or None
            if raw:
                try:
                    eid = int(raw)
                except Exception:
                    eid = None
                if eid is not None:
                    owned = (
                        db.query(Event.EventID)
                        .filter(Event.EventID == eid, Event.UserID == user.UserID)
                        .first()
                    )
                    if owned:
                        selected_event_id = eid
    except Exception:
        selected_event_id = None
    # Check if any deleted remain
    try:
        qdel = (
            db.query(FileMetadata.FileMetadataID)
            .join(Event, Event.EventID == FileMetadata.EventID)
            .filter(Event.UserID == user.UserID, FileMetadata.Deleted)
        )
        if selected_event_id is not None:
            qdel = qdel.filter(Event.EventID == selected_event_id)
        has_deleted_remaining = bool(qdel.first())
    except Exception:
        has_deleted_remaining = True
    # Choose redirect: if none remain, go to default /gallery; else go back to referer
    referer = request.headers.get("referer") or "/gallery"
    redirect_url = "/gallery" if not has_deleted_remaining else referer
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/gallery/actions/permadelete")
async def gallery_permanent_delete(
    request: Request,
    file_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Permanently delete selected files (remove disk files and DB rows), and purge thumbnails."""
    from sqlalchemy import delete

    uid = int(getattr(user, "UserID"))
    files = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == uid, FileMetadata.FileMetadataID.in_(file_ids))
        .all()
    )
    base_paths = []
    for f in files:
        eid = int(getattr(f, "EventID"))
        fname = str(getattr(f, "FileName"))
        base_paths.append((eid, fname, int(getattr(f, "FileMetadataID"))))
    # Delete files from disk and their thumbnails
    for eid, fname, fid in base_paths:
        try:
            path = os.path.join("storage", str(uid), str(eid), fname)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        try:
            cleanup_thumbnails(uid, eid, fid)
        except Exception:
            pass
    # Remove DB rows
    try:
        fid_list = [fid for _, _, fid in base_paths]
        db.execute(
            delete(FileMetadata).where(FileMetadata.FileMetadataID.in_(fid_list))
        )
        db.commit()
    except Exception:
        db.rollback()
    referer = request.headers.get("referer") or "/gallery"
    return RedirectResponse(url=referer, status_code=303)


@router.post("/gallery/download-zip")
async def download_zip(
    request: Request,
    file_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    user_id = user.UserID
    files = _get_user_file_records(db, user_id, file_ids)
    # Enforce plan-based cap for bulk downloads if configured
    try:
        from app.services.billing_utils import get_active_plan

        _plan, features = get_active_plan(db, int(user_id))
        max_zip = int(features.get("max_zip_download_items", 0) or 0)
        if max_zip and len(files) > max_zip:
            files = files[:max_zip]
    except Exception:
        pass
    if not files:
        return RedirectResponse(url=(request.headers.get("referer") or "/gallery"), status_code=303)
    # Build zip in-memory. This is OK for small/medium sets.
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            fname = str(getattr(f, "FileName", ""))
            path = os.path.join("storage", str(user_id), str(f.EventID), fname)
            if os.path.exists(path):
                arcname = os.path.join(str(f.EventID), fname)
                try:
                    zf.write(path, arcname=arcname)
                except Exception:
                    continue
    zip_bytes.seek(0)
    headers = {"Content-Disposition": "attachment; filename=download.zip"}
    return StreamingResponse(zip_bytes, media_type="application/zip", headers=headers)


@router.post("/gallery/favorite")
async def favorite_add(
    file_id: int = Form(...), db: Session = Depends(get_db), user=Depends(require_user)
):
    # Ensure file belongs to user's event
    f = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == user.UserID, FileMetadata.FileMetadataID == file_id)
        .first()
    )
    if not f:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    exists = (
        db.query(FavoriteFile)
        .filter(FavoriteFile.UserID == user.UserID, FavoriteFile.FileMetadataID == file_id)
        .first()
    )
    if not exists:
        db.add(FavoriteFile(UserID=user.UserID, FileMetadataID=file_id))
        db.commit()
    return {"ok": True}


@router.post("/gallery/unfavorite")
async def favorite_remove(
    file_id: int = Form(...), db: Session = Depends(get_db), user=Depends(require_user)
):
    f = (
        db.query(FileMetadata)
        .join(Event, Event.EventID == FileMetadata.EventID)
        .filter(Event.UserID == user.UserID, FileMetadata.FileMetadataID == file_id)
        .first()
    )
    if not f:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    db.query(FavoriteFile).filter(
        FavoriteFile.UserID == user.UserID, FavoriteFile.FileMetadataID == file_id
    ).delete()
    db.commit()
    return {"ok": True}
