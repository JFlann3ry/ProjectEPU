from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.gallery_builders import _build_gallery_files, _build_gallery_ids
from app.api.gallery_scope_resolver import get_scoped_event_id
from app.models.photo_order import EventGalleryOrder
from app.services.auth import require_user
from db import get_db

router = APIRouter()


@router.get("/gallery/data", response_class=JSONResponse)
async def gallery_data(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    type: str | None = Query(None),
    show_deleted: bool = Query(False),
    favorites: bool = Query(False),
    album_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    user_id = user.UserID
    selected_event_id = get_scoped_event_id(request, db, user_id)
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


@router.get("/gallery/ids", response_class=JSONResponse)
async def gallery_all_ids(
    request: Request,
    type: str | None = Query(None),
    show_deleted: bool = Query(False),
    favorites: bool = Query(False),
    album_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Return all FileMetadataIDs in the current gallery scope (no paging).

    Used by the client to implement "Select all" across the full filtered dataset.
    """
    user_id = user.UserID
    selected_event_id = get_scoped_event_id(request, db, user_id)

    ids = _build_gallery_ids(
        db,
        user_id=user_id,
        event_id=selected_event_id,
        type_filter=type,
        show_deleted=show_deleted,
        favorites_only=favorites,
        album_id=album_id,
    )
    return JSONResponse({"ok": True, "ids": ids, "count": len(ids)})
