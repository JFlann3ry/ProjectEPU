# ruff: noqa: I001
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import case
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.models.album import Album, AlbumPhoto
from app.models.event import Event, FavoriteFile, FileMetadata
from app.models.photo_order import EventGalleryOrder

# Cache DB feature detection for optional columns.
_HAS_DELETED_AT: Optional[bool] = None


def _to_utc_aware(dt: datetime | None) -> datetime | None:
    if not isinstance(dt, datetime):
        return None
    try:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


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
    event_query = db.query(Event).filter(Event.UserID == user_id)
    if event_id is not None:
        event_query = event_query.filter(Event.EventID == event_id)
    event_ids = [e.EventID for e in event_query.all()]
    if not event_ids:
        return [], False

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

    if album_id is not None:
        try:
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

    if show_deleted:
        q = q.filter(FileMetadata.Deleted)
    else:
        q = q.filter(~FileMetadata.Deleted)

    if type_filter in ("image", "video"):
        prefix = f"{type_filter}/"
        q = q.filter(FileMetadata.FileType.like(prefix + "%"))

    fav_ids = set()
    if favorites_only:
        fav_rows = (
            db.query(FavoriteFile.FileMetadataID).filter(FavoriteFile.UserID == user_id).all()
        )
        fav_ids = set(int(r[0]) for r in fav_rows)
        if not fav_ids:
            return [], False
        q = q.filter(FileMetadata.FileMetadataID.in_(fav_ids))

    q = q.order_by(
        case((FileMetadata.CapturedDateTime.is_(None), 1), else_=0),
        FileMetadata.CapturedDateTime.asc(),
        FileMetadata.UploadDate.asc(),
        FileMetadata.FileMetadataID.asc(),
    )
    files: list[dict] = []
    if not favorites_only:
        fav_rows2 = (
            db.query(FavoriteFile.FileMetadataID).filter(FavoriteFile.UserID == user_id).all()
        )
        fav_ids = set(int(r[0]) for r in fav_rows2)

    order_ids: list[int] = []
    if event_id is not None:
        try:
            from sqlalchemy import text

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

    rows: list = []
    has_more = False
    if order_ids:
        try:
            all_rows = list(q)
            idx_id = 0
            by_id = {int(r[idx_id]): r for r in all_rows}
            ordered_rows: list = []
            for fid in order_ids:
                if fid in by_id:
                    ordered_rows.append(by_id.pop(fid))
            if by_id:
                for r in all_rows:
                    try:
                        rid = int(r[idx_id])
                    except Exception:
                        continue
                    if rid in by_id:
                        ordered_rows.append(by_id.pop(rid))
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
            rows = []
            has_more = False

    if not order_ids:
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

    idx_id = 0
    idx_event = 1
    idx_name = 2
    idx_filetype = 3
    idx_captured = 4
    idx_deleted = 6
    idx_deleted_at = 7 if has_del_at else None

    now_utc = datetime.now(timezone.utc)
    for row in rows:
        ftype = "other"
        ctype = (row[idx_filetype] or "") if row is not None else ""
        if ctype.startswith("image"):
            ftype = "image"
        elif ctype.startswith("video"):
            ftype = "video"
        thumb_url = None
        if ftype in ("image", "video"):
            thumb_url = f"/thumbs/{row[idx_id]}.jpg?w=720"

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

        deleted_flag = bool(row[idx_deleted])
        deleted_at = row[idx_deleted_at] if (has_del_at and idx_deleted_at is not None) else None
        deleted_at_utc = _to_utc_aware(deleted_at)
        days_left = None
        permanent_delete_date = None
        if deleted_flag:
            if has_del_at and deleted_at_utc is not None:
                try:
                    delta_days = (now_utc - deleted_at_utc).days
                    days_left = max(0, 30 - max(0, delta_days))
                    try:
                        pdel = deleted_at_utc + timedelta(days=30)
                        permanent_delete_date = pdel.date().isoformat()
                    except Exception:
                        permanent_delete_date = None
                except Exception:
                    days_left = None
            else:
                if show_deleted:
                    days_left = 9999

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
                        days_label = f"{days_left} days left"
            except Exception:
                days_label = None

        thumb_480 = f"/thumbs/{row[idx_id]}.jpg?w=480" if ftype in ("image", "video") else None
        thumb_720 = f"/thumbs/{row[idx_id]}.jpg?w=720" if ftype in ("image", "video") else None
        thumb_960 = f"/thumbs/{row[idx_id]}.jpg?w=960" if ftype in ("image", "video") else None
        thumb_1440 = f"/thumbs/{row[idx_id]}.jpg?w=1440" if ftype in ("image", "video") else None

        files.append(
            {
                "id": row[idx_id],
                "event_id": row[idx_event],
                "type": ftype,
                "url": f"/media/{user_id}/{row[idx_event]}/{row[idx_name]}",
                "thumb_url": thumb_url,
                "thumbnail_480": thumb_480,
                "thumbnail_720": thumb_720,
                "thumbnail_960": thumb_960,
                "thumbnail_1440": thumb_1440,
                "srcset": srcset,
                "name": row[idx_name],
                "datetime": (row[idx_captured].isoformat() if row[idx_captured] else None),
                "deleted": deleted_flag,
                "deleted_at": (deleted_at.isoformat() if deleted_at else None),
                "days_left": days_left,
                "permanent_delete_date": permanent_delete_date,
                "days_label": days_label,
                "favorite": (row[idx_id] in fav_ids),
            }
        )

    try:
        if show_deleted and files:
            files.sort(
                key=lambda f: (
                    (f.get("permanent_delete_date") is None),
                    f.get("permanent_delete_date") or "9999-12-31",
                )
            )
    except Exception:
        pass
    return files, has_more


def _build_gallery_ids(
    db: Session,
    user_id: int,
    event_id: int | None,
    type_filter: str | None,
    show_deleted: bool,
    favorites_only: bool = False,
    album_id: int | None = None,
):
    event_query = db.query(Event).filter(Event.UserID == user_id)
    if event_id is not None:
        event_query = event_query.filter(Event.EventID == event_id)
    event_ids = [e.EventID for e in event_query.all()]
    if not event_ids:
        return []

    q = db.query(FileMetadata.FileMetadataID).filter(FileMetadata.EventID.in_(event_ids))

    if album_id is not None:
        try:
            alb = db.query(Album).filter(Album.AlbumID == album_id).first()
            a_eid = None
            if alb is not None:
                raw_eid = getattr(alb, "EventID", None)
                try:
                    a_eid = int(raw_eid) if raw_eid is not None else None
                except Exception:
                    a_eid = None
            if not alb or a_eid not in event_ids:
                return []
            rows_fp = db.query(AlbumPhoto.FileID).filter(AlbumPhoto.AlbumID == album_id).all()
            file_ids = set()
            for r in rows_fp or []:
                try:
                    file_ids.add(int(r[0]))
                except Exception:
                    continue
            if not file_ids:
                return []
            q = q.filter(FileMetadata.FileMetadataID.in_(file_ids))
        except Exception:
            return []

    if show_deleted:
        q = q.filter(FileMetadata.Deleted)
    else:
        q = q.filter(~FileMetadata.Deleted)

    if type_filter in ("image", "video"):
        prefix = f"{type_filter}/"
        q = q.filter(FileMetadata.FileType.like(prefix + "%"))

    if favorites_only:
        fav_rows = (
            db.query(FavoriteFile.FileMetadataID).filter(FavoriteFile.UserID == user_id).all()
        )
        fav_ids = set(int(r[0]) for r in fav_rows)
        if not fav_ids:
            return []
        q = q.filter(FileMetadata.FileMetadataID.in_(fav_ids))

    if event_id is not None:
        try:
            from sqlalchemy import text

            sql = text("EXEC dbo.GetEventGalleryOrder :eid")
            res = db.execute(sql.bindparams(eid=event_id))
            rows_sp = res.fetchall()
            order_ids = [int(r[0]) for r in rows_sp] if rows_sp else []
            if order_ids:
                allowed_ids = set(int(r[0]) for r in q.all())
                return [fid for fid in order_ids if fid in allowed_ids]
        except Exception:
            pass

    q = q.order_by(
        case((FileMetadata.CapturedDateTime.is_(None), 1), else_=0),
        FileMetadata.CapturedDateTime.asc(),
        FileMetadata.UploadDate.asc(),
        FileMetadata.FileMetadataID.asc(),
    )
    try:
        rows = q.all()
    except Exception:
        rows = []
    ids: list[int] = []
    for r in rows or []:
        try:
            ids.append(int(r[0]))
        except Exception:
            continue
    return ids
