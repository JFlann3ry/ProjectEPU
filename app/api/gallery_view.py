from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.gallery_builders import _build_gallery_files, _has_deleted_at
from app.api.gallery_scope_resolver import get_scoped_event_id
from app.core.templates import templates
from app.models.event import Event, FavoriteFile, FileMetadata
from app.models.photo_order import EventGalleryOrder
from app.services.auth import require_user
from app.services.csrf import issue_csrf_token, set_csrf_cookie
from db import get_db

router = APIRouter()


@router.get("/gallery", response_class=HTMLResponse)
async def user_gallery(
    request: Request,
    type: str | None = Query(None),
    show_deleted: bool = Query(False),
    favorites: bool = Query(False),
    album_id: int | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    user_id = user.UserID
    selected_event_id = get_scoped_event_id(request, db, user_id)
    page_size = int(limit or 100)

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
            base = _count_base(eids)
            if favorites:
                base = base.join(
                    FavoriteFile,
                    FavoriteFile.FileMetadataID == FileMetadata.FileMetadataID,
                ).filter(FavoriteFile.UserID == user_id)
            cur_del = show_deleted
            base_cur = base.filter(FileMetadata.Deleted == cur_del)
            counts["all"] = base_cur.count()
            counts["images"] = base_cur.filter(FileMetadata.FileType.like("image/%")).count()
            counts["videos"] = base_cur.filter(FileMetadata.FileType.like("video/%")).count()

            fav_q = _count_base(eids)
            fav_q = fav_q.filter(FileMetadata.Deleted == cur_del)
            if type in ("image", "video"):
                fav_q = fav_q.filter(FileMetadata.FileType.like(f"{type}/%"))
            fav_q = fav_q.join(
                FavoriteFile,
                FavoriteFile.FileMetadataID == FileMetadata.FileMetadataID,
            ).filter(FavoriteFile.UserID == user_id)
            counts["favorites"] = fav_q.count()

            del_q = _count_base(eids)
            if favorites:
                del_q = del_q.join(
                    FavoriteFile,
                    FavoriteFile.FileMetadataID == FileMetadata.FileMetadataID,
                ).filter(FavoriteFile.UserID == user_id)
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
        limit=page_size,
        offset=int(offset or 0),
        album_id=album_id,
    )

    if show_deleted and files:
        for f in files:
            try:
                dl = f.get("days_left")
                if not isinstance(dl, int):
                    f["days_left"] = 9999
            except Exception:
                try:
                    f["days_left"] = 9999
                except Exception:
                    pass

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
                                return int(v) if v is not None else 2**60
                            except Exception:
                                return 2**60

                        files.sort(key=_ord_key)
                except Exception:
                    pass
    except Exception:
        pass

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
        selected_event_id = selected_event_id or None

    token = issue_csrf_token(request.cookies.get("session_id"))
    cur_offset = int(offset or 0)
    next_offset = (cur_offset + len(files)) if has_more else None
    prev_offset = (cur_offset - page_size) if cur_offset > 0 else None
    if isinstance(prev_offset, int) and prev_offset < 0:
        prev_offset = 0

    event_name: str | None = None
    event_code: str | None = None
    try:
        if selected_event_id:
            row = (
                db.query(Event.Name, Event.Code)
                .filter(Event.EventID == selected_event_id, Event.UserID == user_id)
                .first()
            )
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

    ctx = {
        "request": request,
        "event_id": selected_event_id or 0,
        "event_name": event_name,
        "event_code": event_code,
        "files": files,
        "next_offset": next_offset,
        "prev_offset": prev_offset,
        "current_offset": cur_offset,
        "page_size": page_size,
        "filters": {"type": type, "show_deleted": show_deleted, "favorites": favorites},
        "counts": counts,
        "has_deleted": bool(_has_deleted_at(db)),
        "csrf_token": token,
    }
    resp = templates.TemplateResponse(request, "gallery.html", context=ctx)
    set_csrf_cookie(resp, token, httponly=False)
    return resp
