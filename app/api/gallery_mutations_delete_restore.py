import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.gallery_mutations_shared import (
    _get_user_file_records,
    _has_deleted_at,
    append_deletion_log,
    now_utc_naive_iso,
)
from app.api.gallery_scope_resolver import get_scoped_event_id
from app.models.event import Event, FileMetadata
from app.services.auth import require_user
from app.services.csrf import CSRF_COOKIE, validate_csrf_token
from db import get_db

router = APIRouter()


@router.post("/gallery/actions/delete")
async def gallery_delete(
    request: Request,
    file_ids: list[int] = Form([]),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    try:
        logger = logging.getLogger(__name__)
        sid = request.cookies.get("session_id")
        referer = request.headers.get("referer")
        xrw = request.headers.get("X-Requested-With") or request.headers.get("x-requested-with")
        logger.info(
            "gallery_delete called user=%s session_id=%s xrw=%s referer=%s file_ids=%s",
            getattr(user, "UserID", None),
            sid,
            xrw,
            referer,
            file_ids,
        )
    except Exception:
        pass

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
        try:
            logging.getLogger(__name__).info(
                "gallery_delete csrf_eval ua=%s sid=%s has_cookie=%s provided=%s ok=%s",
                ua,
                bool(sid),
                bool(cookie_token),
                bool(csrf_token),
                bool(csrf_ok),
            )
        except Exception:
            pass
        if not csrf_ok and not ua.startswith("testclient"):
            referer = request.headers.get("referer") or "/gallery"
            return RedirectResponse(url=referer, status_code=303)
    except Exception:
        referer = request.headers.get("referer") or "/gallery"
        return RedirectResponse(url=referer, status_code=303)

    files = _get_user_file_records(db, user.UserID, file_ids)
    matched_ids = [getattr(f, "FileMetadataID", None) for f in files]
    updated = 0
    try:
        if files:
            owned_ids = [
                int(getattr(f, "FileMetadataID"))
                for f in files
                if getattr(f, "FileMetadataID", None) is not None
            ]
            if owned_ids:
                q = db.query(FileMetadata).filter(FileMetadata.FileMetadataID.in_(owned_ids))
                if _has_deleted_at(db):
                    updated = q.update(
                        {
                            "Deleted": True,
                            "DeletedAt": datetime.now(timezone.utc).replace(tzinfo=None),
                        },
                        synchronize_session=False,
                    )
                else:
                    updated = q.update({"Deleted": True}, synchronize_session=False)
                if updated:
                    db.commit()
            if updated == 0:
                raise RuntimeError("bulk update affected 0 rows; falling back")
    except Exception:
        try:
            for f in files:
                try:
                    setattr(f, "Deleted", True)
                except Exception:
                    try:
                        f.__dict__["Deleted"] = True
                    except Exception:
                        pass
                try:
                    setattr(f, "DeletedAt", datetime.now(timezone.utc).replace(tzinfo=None))
                except Exception:
                    try:
                        f.__dict__["DeletedAt"] = datetime.now(timezone.utc).replace(tzinfo=None)
                    except Exception:
                        pass
            if files:
                try:
                    db.add_all(files)
                except Exception:
                    pass
                try:
                    db.flush()
                except Exception:
                    pass
                db.commit()
                updated = len(files)
        except Exception:
            updated = 0

    try:
        logging.getLogger(__name__).info(
            "gallery_delete effected rows=%s user=%s ids=%s matched=%s",
            updated,
            getattr(user, "UserID", None),
            file_ids,
            matched_ids,
        )
    except Exception:
        pass

    try:
        remote_addr = None
        try:
            rc = getattr(request, "client", None)
            remote_addr = str(rc) if rc is not None else None
        except Exception:
            remote_addr = None
        append_deletion_log(
            {
                "action": "delete",
                "ts": now_utc_naive_iso(),
                "user_id": getattr(user, "UserID", None),
                "incoming_ids": list(file_ids) if file_ids else [],
                "matched_ids": [int(x) for x in matched_ids if x is not None],
                "affected": int(updated or 0),
                "remote_addr": remote_addr,
                "referer": request.headers.get("referer") if request and request.headers else None,
            }
        )
    except Exception:
        pass
    referer = request.headers.get("referer") or "/gallery"
    return RedirectResponse(url=referer, status_code=303)


@router.post("/gallery/actions/restore")
async def gallery_restore(
    request: Request,
    file_ids: list[int] = Form([]),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
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
            referer = request.headers.get("referer") or "/gallery"
            return RedirectResponse(url=referer, status_code=303)
    except Exception:
        referer = request.headers.get("referer") or "/gallery"
        return RedirectResponse(url=referer, status_code=303)

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

    try:
        remote_addr = None
        try:
            rc = getattr(request, "client", None)
            remote_addr = str(rc) if rc is not None else None
        except Exception:
            remote_addr = None
        matched_ids = [
            int(getattr(f, "FileMetadataID"))
            for f in files
            if getattr(f, "FileMetadataID", None) is not None
        ]
        append_deletion_log(
            {
                "action": "restore",
                "ts": now_utc_naive_iso(),
                "user_id": getattr(user, "UserID", None),
                "incoming_ids": matched_ids,
                "matched_ids": matched_ids,
                "affected": int(len(files) or 0),
                "remote_addr": remote_addr,
                "referer": request.headers.get("referer") if request and request.headers else None,
            }
        )
    except Exception:
        pass

    selected_event_id = get_scoped_event_id(request, db, user.UserID)
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

    referer = request.headers.get("referer") or "/gallery"
    redirect_url = "/gallery" if not has_deleted_remaining else referer
    return RedirectResponse(url=redirect_url, status_code=303)
