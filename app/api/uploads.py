"""Uploads endpoints."""

# ruff: noqa: I001
import logging
import os
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.event import (
    Event,
    EventCustomisation as EC,
    EventStorage,
    FileMetadata,
    GuestMessage,
    GuestSession,
    Theme as ThemeModel,
)
from app.services.mime_utils import is_allowed_mime
from db import get_db
from app.services.thumbs import generate_all_thumbs_for_file

router = APIRouter()
audit = logging.getLogger("audit")
PAGE_SIZE = 24


# Guest upload page (GET)
@router.get("/guest/upload/{event_code}", response_class=HTMLResponse)
async def guest_upload_page(request: Request, event_code: str, db: Session = Depends(get_db)):
    theme = None
    event = db.query(Event).filter(Event.Code == event_code).first()
    # Attach customisation for template convenience
    if event:
        custom = db.query(EC).filter(EC.EventID == event.EventID).first()
        setattr(event, "eventcustomisation", custom)
        try:
            if custom and getattr(custom, "ThemeID", None):
                theme = (
                    db.query(ThemeModel)
                    .filter(ThemeModel.ThemeID == custom.ThemeID)
                    .first()
                )
        except Exception:
            theme = None
    audit.info(
        "guest.upload.page",
        extra={
            "event_code": event_code,
            "event_id": getattr(event, "EventID", None) if event else None,
            "client": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    if not event:
        # Return 200 with inline error to keep guest flow simple and match smoke test expectations
        return templates.TemplateResponse(
            request,
            "guest_upload.html",
            context={
                "event_code": event_code,
                "event": None,
                "error": "Invalid event code.",
            },
        )
    # Block unpublished events from guest upload
    if not getattr(event, "Published", False):
        return templates.TemplateResponse(
            request,
            "guest_upload.html",
            context={
                "event_code": event_code,
                "event": None,
                "error": "This event is not available yet.",
            },
            status_code=403,
        )
    # Load recent uploads for this guest (cookie-scoped)
    guest_files = []
    has_more = False
    try:
        cookie_name = f"guest_session_{event.Code}"
        guest_cookie = request.cookies.get(cookie_name)
        if guest_cookie:
            base_q = db.query(FileMetadata).filter(
                FileMetadata.EventID == int(getattr(event, "EventID")),
                FileMetadata.GuestID == int(guest_cookie),
                ~FileMetadata.Deleted,
            )
            total = base_q.count()
            files = (
                base_q.order_by(FileMetadata.UploadDate.desc()).limit(PAGE_SIZE).offset(0).all()
            )
            has_more = total > PAGE_SIZE
            uid = int(getattr(event, "UserID"))
            eid = int(getattr(event, "EventID"))
            base = f"/storage/{uid}/{eid}/"
            # Shape for template with lightweight metadata
            for f in files:
                size = int(getattr(f, "FileSize", 0) or 0)
                if size >= 1024 * 1024:
                    size_label = f"{size/(1024*1024):.1f} MB"
                elif size >= 1024:
                    size_label = f"{size/1024:.0f} KB"
                else:
                    size_label = f"{size} B"
                dt = getattr(f, "UploadDate", None)
                try:
                    uploaded_display = dt.strftime("%Y-%m-%d %H:%M") if dt else ""
                except Exception:
                    uploaded_display = ""
                guest_files.append(
                    {
                        "id": int(getattr(f, "FileMetadataID")),
                        "name": getattr(f, "FileName"),
                        "type": getattr(f, "FileType"),
                        "url": base + getattr(f, "FileName"),
                        "size": size_label,
                        "uploaded": uploaded_display,
                    }
                )
    except Exception:
        guest_files = []
    return templates.TemplateResponse(
        request,
        "guest_upload.html",
        context={
            "event_code": event_code,
            "event": event,
            "theme": (theme if event else None),
            "guest_files": guest_files,
            "guest_has_more": has_more,
            "guest_page_size": PAGE_SIZE,
        },
    )


# Guest upload page (POST, with file saving and metadata recording)
@router.post("/guest/upload/{event_code}", response_class=HTMLResponse)
async def guest_upload_post(
    request: Request,
    event_code: str,
    files: list[UploadFile] = File(...),
    guest_email: str = Form(None),
    guest_message: str = Form(None),
    display_name: str = Form(None),
    device_type: str = Form(None),
    terms: bool = Form(False),
    db: Session = Depends(get_db),
):

    event = db.query(Event).filter(Event.Code == event_code).first()
    uploaded = []
    guest_session = None
    guest_id = None
    if event:
        # Reject uploads for unpublished events
        if not getattr(event, "Published", False):
            return templates.TemplateResponse(
                request,
                "guest_upload.html",
                context={
                    "event_code": event_code,
                    "event": None,
                    "error": "This event is not available yet.",
                },
                status_code=403,
            )
        user_id = int(getattr(event, "UserID"))
        event_id = int(getattr(event, "EventID"))
        # Load plan features
        try:
            from app.services.billing_utils import get_active_plan

            _plan, features = get_active_plan(db, user_id)
            max_guests = int(features.get("max_guests_per_event", 0) or 0)
            plan_storage_mb = int(features.get("max_storage_per_event_mb", 0) or 0)
        except Exception:
            max_guests = 0
            plan_storage_mb = 0

        # Enforce guest cap (counts distinct guest sessions). If an existing
        # session is found, don't count it as new.
        existing_session = (
            db.query(GuestSession)
            .filter(
                GuestSession.EventID == event_id,
                GuestSession.GuestEmail == guest_email,
                GuestSession.DeviceType == device_type,
            )
            .first()
        )
        if max_guests > 0:
            total_guests = (
                db.query(GuestSession.GuestID).filter(GuestSession.EventID == event_id).count()
            )
            if not existing_session and total_guests >= max_guests:
                return templates.TemplateResponse(
                    request,
                    "guest_upload.html",
                    context={
                        "event_code": event_code,
                        "event": event,
                        "error": (
                            "Guest limit reached for this event. Please "
                            "<a href='/pricing'>choose a package</a> to allow more "
                            "guests."
                        ),
                    },
                    status_code=400,
                )

        # Find or create GuestSession
        guest_session = existing_session
        if not guest_session:
            guest_session = GuestSession(
                EventID=event_id,
                DeviceType=device_type,
                GuestEmail=guest_email,
                TermsChecked=terms,
            )
            db.add(guest_session)
            db.commit()
            db.refresh(guest_session)
        else:
            setattr(guest_session, "TermsChecked", bool(terms))
            db.commit()
        guest_id = guest_session.GuestID
        # Ensure event storage layout exists: base/, uploads/, thumbnails/
        event_base_path = os.path.join("storage", str(user_id), str(event_id))
        uploads_base = os.path.join(event_base_path, "uploads")
        thumbs_base = os.path.join(event_base_path, "thumbnails")
        os.makedirs(uploads_base, exist_ok=True)
        os.makedirs(thumbs_base, exist_ok=True)
        # Keep storage_path variable for compatibility with downstream accounting
        storage_path = event_base_path

        upload_count = 0
        from app.services.metadata_utils import (
            extract_image_metadata,
            extract_video_metadata,
        )

        total_bytes = 0
        duplicate_count = 0
        # Validation helpers
        allowed_prefixes = tuple(
            getattr(settings, "ALLOWED_UPLOAD_MIME_PREFIXES", ("image/", "video/"))
        )
        max_bytes = int(getattr(settings, "MAX_UPLOAD_BYTES", 200_000_000))

        def safe_name(name: str) -> str:
            name = name.replace("\\", "/").split("/")[-1]
            # allow alnum, dash, underscore, dot; strip others
            return re.sub(r"[^A-Za-z0-9._-]", "_", name)

        def unique_path(base_dir: str, fname: str) -> str:
            root, ext = os.path.splitext(fname)
            candidate = os.path.join(base_dir, fname)
            idx = 1
            while os.path.exists(candidate):
                candidate = os.path.join(base_dir, f"{root}_{idx}{ext}")
                idx += 1
            return candidate

        # Optional guest message handling (rate-limited per guest session)
        try:
            raw_msg = (guest_message or "").strip()
            if raw_msg:
                # simple rate limit: max 3 messages per 10 minutes per guest session
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                ten_min_ago = now - timedelta(minutes=10)
                recent = (
                    db.query(GuestMessage)
                    .filter(
                        GuestMessage.EventID == event_id,
                        GuestMessage.GuestSessionID == guest_id,
                        GuestMessage.CreatedAt >= ten_min_ago,
                    )
                    .count()
                )
                if recent < 3:
                    # sanitize length and basic content
                    msg = raw_msg[:300]
                    name = (display_name or "").strip()[:80] or None
                    gm = GuestMessage(
                        EventID=event_id, GuestSessionID=guest_id, DisplayName=name, Message=msg
                    )
                    db.add(gm)
                    db.commit()
                else:
                    audit.info(
                        "guest.message.rate_limited",
                        extra={
                            "event_id": event_id,
                            "guest_id": guest_id,
                            "request_id": getattr(request.state, "request_id", None),
                        },
                    )
        except Exception:
            pass

    # Precompute storage cap enforcement before writing files
    # Determine effective storage limit in MB: plan feature overrides
    # optional custom message value
        custom_limit_mb = None
        try:
            _c = db.query(EC).filter(EC.EventID == event_id).first()
            msg = getattr(_c, "StorageLimitMessage", None) if _c else None
            if msg and str(msg).strip().isdigit():
                custom_limit_mb = int(str(msg).strip())
        except Exception:
            custom_limit_mb = None
        effective_limit_mb = int(plan_storage_mb or 0) or int(custom_limit_mb or 0)
        allowed_prefixes = tuple(
            getattr(settings, "ALLOWED_UPLOAD_MIME_PREFIXES", ("image/", "video/"))
        )
        max_bytes = int(getattr(settings, "MAX_UPLOAD_BYTES", 200_000_000))
        candidate_bytes = 0
        prechecked_files = []  # (contents, sniffed, filename)
        for file in files:
            if not file.filename:
                continue
            ctype = getattr(file, "content_type", "") or ""
            contents = await file.read()
            allowed, sniffed = is_allowed_mime(
                contents, allowed_prefixes=allowed_prefixes, fallback_content_type=ctype
            )
            if allowed_prefixes and not allowed:
                audit.warning(
                    "guest.upload.rejected_mime",
                    extra={
                        "event_id": event_id,
                        "ctype": sniffed,
                        "request_id": getattr(request.state, "request_id", None),
                    },
                )
                continue
            if max_bytes and len(contents) > max_bytes:
                audit.warning(
                    "guest.upload.rejected_size",
                    extra={
                        "event_id": event_id,
                        "size": len(contents),
                        "request_id": getattr(request.state, "request_id", None),
                    },
                )
                continue
            prechecked_files.append((contents, sniffed, file.filename))
            candidate_bytes += len(contents)

        # Enforce storage cap (if any) using current usage + candidate size
        if effective_limit_mb and effective_limit_mb > 0:
            base = os.path.join("storage", str(user_id), str(event_id))
            current = 0
            if os.path.exists(base):
                for root, _, filenames in os.walk(base):
                    for fn in filenames:
                        p = os.path.join(root, fn)
                        try:
                            current += os.path.getsize(p)
                        except Exception:
                            pass
            if (current + candidate_bytes) > (effective_limit_mb * 1024 * 1024):
                return templates.TemplateResponse(
                    request,
                    "guest_upload.html",
                    context={
                        "event_code": event_code,
                        "event": event,
                        "error": (
                            "Storage limit reached for this event. Please "
                            "<a href='/billing'>upgrade your plan</a> to continue."
                        ),
                    },
                    status_code=400,
                )

        # Proceed with writes and metadata after enforcement
        # Get S3 service if configured
        s3_service = getattr(request.app.state, "s3_service", None)
        
        for contents, sniffed, orig_name in prechecked_files:
            fname = safe_name(orig_name)
            total_bytes += len(contents)
            
            # Extract metadata (requires temporary file or in-memory processing)
            tmp_path = None
            try:
                if sniffed.startswith("image") or sniffed.startswith("video"):
                    # Create temp file for metadata extraction
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(fname)[1]) as tf:
                        tf.write(contents)
                        tmp_path = tf.name
                    
                    if sniffed.startswith("image"):
                        meta = extract_image_metadata(tmp_path)
                    else:
                        meta = extract_video_metadata(tmp_path)
                else:
                    meta = {"datetime_taken": None, "gps_lat": None, "gps_long": None, "checksum": None}
            except Exception as e:
                logging.warning(f"Failed to extract metadata: {e}")
                meta = {"datetime_taken": None, "gps_lat": None, "gps_long": None, "checksum": None}
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
            
            # Duplicate detection: same checksum within the same event
            checksum = meta.get("checksum")
            is_duplicate = False
            if checksum:
                exists = (
                    db.query(FileMetadata)
                    .filter(
                        FileMetadata.EventID == event_id,
                        FileMetadata.Checksum == checksum,
                        ~FileMetadata.Deleted,
                    )
                    .first()
                )
                if exists:
                    is_duplicate = True
            if is_duplicate:
                duplicate_count += 1
                continue
            
            # Save metadata
            stored_name = fname
            metadata = FileMetadata(
                EventID=event_id,
                GuestID=guest_id,
                FileName=stored_name,
                FileType=sniffed,
                FileSize=len(contents),
                CapturedDateTime=meta.get("datetime_taken"),
                GPSLat=str(meta.get("gps_lat")) if meta.get("gps_lat") is not None else None,
                GPSLong=str(meta.get("gps_long")) if meta.get("gps_long") is not None else None,
                Checksum=meta.get("checksum"),
            )
            db.add(metadata)
            db.flush()  # Flush to get FileMetadataID
            
            # Upload to S3 if configured, otherwise save to local filesystem
            if s3_service:
                s3_key = f"uploads/{user_id}/{event_id}/{metadata.FileMetadataID}/{stored_name}"
                try:
                    s3_service.upload_file(contents, s3_key, sniffed)
                    logging.info(f"Uploaded {s3_key} to S3")
                except Exception as e:
                    logging.error(f"S3 upload failed for {s3_key}: {e}")
                    # Fall back to local filesystem
                    tmp_path = unique_path(uploads_base, fname)
                    with open(tmp_path, "wb") as buffer:
                        buffer.write(contents)
            else:
                # Fall back to local filesystem
                tmp_path = unique_path(uploads_base, fname)
                with open(tmp_path, "wb") as buffer:
                    buffer.write(contents)
            
            uploaded.append(stored_name)
            upload_count += 1

        # Update UploadCount
        setattr(
            guest_session,
            "UploadCount",
            int(getattr(guest_session, "UploadCount", 0) or 0) + upload_count,
        )
        db.commit()
    # Fire-and-forget background thumb generation to avoid on-demand cost
        try:
            import threading

            def _thumb_job(uid: int, eid: int, recs: list[FileMetadata]):
                for r in recs:
                    try:
                        generate_all_thumbs_for_file(
                            user_id=uid,
                            event_id=eid,
                            file_id=int(getattr(r, "FileMetadataID")),
                            file_type=str(getattr(r, "FileType")),
                            file_name=str(getattr(r, "FileName")),
                            widths=(480, 720, 960, 1440),
                        )
                    except Exception:
                        pass

            # Collect the newly added metadata rows to pass to the thread
            new_recs = (
                db.query(FileMetadata)
                .filter(FileMetadata.EventID == event_id)
                .order_by(FileMetadata.FileMetadataID.desc())
                .limit(upload_count)
                .all()
            )
            t = threading.Thread(target=_thumb_job, args=(user_id, event_id, new_recs), daemon=True)
            t.start()
        except Exception:
            pass
        # Rebuild gallery order synchronously so newly uploaded files appear
        # in the EventGalleryOrder table immediately for UI and API consumers.
        try:
            from app.services.photo_order_service import rebuild_event_gallery_order

            try:
                rebuild_event_gallery_order(db, event_id)
            except Exception:
                # Non-fatal: don't fail upload on ordering issues
                audit.exception("guest.upload.order_rebuild_failed", extra={"event_id": event_id})
        except Exception:
            pass
        audit.info(
            "guest.upload.completed",
            extra={
                "event_id": event_id,
                "guest_id": guest_id,
                "files_count": upload_count,
                "total_bytes": total_bytes,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        # Update or create EventStorage usage to reflect current on-disk size
        try:
            # Recalculate current bytes in the event storage folder
            current_bytes = 0
            if os.path.exists(storage_path):
                for root, _, filenames in os.walk(storage_path):
                    for fn in filenames:
                        fp = os.path.join(root, fn)
                        try:
                            current_bytes += os.path.getsize(fp)
                        except Exception:
                            pass
            current_mb = int(current_bytes / (1024 * 1024))
            # Upsert EventStorage row
            es = (
                db.query(EventStorage)
                .filter(EventStorage.EventID == event_id)
                .order_by(EventStorage.EventStorageID.desc())
                .first()
            )
            # Persist effective limit if available for visibility
            try:
                storage_limit_mb = int(effective_limit_mb or 0)
            except Exception:
                storage_limit_mb = 0
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if es is None:
                es = EventStorage(
                    EventID=event_id,
                    StoragePath=storage_path,
                    StorageLimitMB=storage_limit_mb,
                    CurrentUsageMB=current_mb,
                    LastUploadDateTime=now,
                )
                db.add(es)
            else:
                try:
                    setattr(es, "StoragePath", storage_path or getattr(es, "StoragePath", None))
                except Exception:
                    pass
                # only update StorageLimitMB if it's zero/unset and we have a plan-derived limit
                try:
                    if int(getattr(es, "StorageLimitMB", 0) or 0) == 0 and storage_limit_mb > 0:
                        setattr(es, "StorageLimitMB", storage_limit_mb)
                except Exception:
                    pass
                try:
                    setattr(es, "CurrentUsageMB", current_mb)
                    setattr(es, "LastUploadDateTime", now)
                except Exception:
                    pass
            db.commit()
        except Exception:
            # Non-blocking: do not fail the request on accounting issues
            pass
    # No top-of-page message, handled by JS in form
    # Include theme for fallback
    theme = None
    try:
        if event:
            custom = db.query(EC).filter(EC.EventID == int(getattr(event, "EventID"))).first()
            if custom and getattr(custom, "ThemeID", None):
                theme = db.query(ThemeModel).filter(ThemeModel.ThemeID == custom.ThemeID).first()
    except Exception:
        theme = None
    resp = templates.TemplateResponse(
        request,
        "guest_upload.html",
        context={"event_code": event_code, "event": event, "theme": theme},
        headers={"X-Duplicates-Skipped": str(duplicate_count if event else 0)},
    )
    # Persist guest session cookie for listing/deleting their own uploads later
    try:
        if (guest_id is not None) and (event is not None):
            cookie_name = f"guest_session_{event.Code}"
            resp.set_cookie(cookie_name, str(guest_id), max_age=60 * 60 * 24 * 30, samesite="lax")
    except Exception:
        pass
    return resp


@router.post("/guest/upload/{event_code}/delete")
async def guest_delete_file(
    request: Request, event_code: str, file_id: int = Form(...), db: Session = Depends(get_db)
):
    """Allow a guest to soft-delete one of their own recent uploads.

    Uses their cookie-scoped GuestSession for authorization.
    """
    event = db.query(Event).filter(Event.Code == event_code).first()
    if not event:
        return JSONResponse({"ok": False, "error": "Invalid event."}, status_code=404)
    cookie_name = f"guest_session_{event.Code}"
    guest_cookie = request.cookies.get(cookie_name)
    if not guest_cookie:
        return JSONResponse({"ok": False, "error": "Not authorized."}, status_code=403)
    rec = (
        db.query(FileMetadata)
        .filter(
            FileMetadata.FileMetadataID == int(file_id),
            FileMetadata.EventID == int(getattr(event, "EventID")),
            FileMetadata.GuestID == int(guest_cookie),
            ~FileMetadata.Deleted,
        )
        .first()
    )
    if not rec:
        return JSONResponse({"ok": False, "error": "Not found."}, status_code=404)
    # Soft delete
    setattr(rec, "Deleted", True)
    db.commit()
    audit.info(
        "guest.upload.delete",
        extra={
            "event_id": int(getattr(event, "EventID")),
            "file_id": int(getattr(rec, "FileMetadataID")),
            "guest_id": int(guest_cookie),
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return JSONResponse({"ok": True})


@router.post("/guest/upload/{event_code}/restore")
async def guest_restore_file(
    request: Request, event_code: str, file_id: int = Form(...), db: Session = Depends(get_db)
):
    """Allow a guest to undo a recent soft-delete (restore their own file)."""
    event = db.query(Event).filter(Event.Code == event_code).first()
    if not event:
        return JSONResponse({"ok": False, "error": "Invalid event."}, status_code=404)
    cookie_name = f"guest_session_{event.Code}"
    guest_cookie = request.cookies.get(cookie_name)
    if not guest_cookie:
        return JSONResponse({"ok": False, "error": "Not authorized."}, status_code=403)
    rec = (
        db.query(FileMetadata)
        .filter(
            FileMetadata.FileMetadataID == int(file_id),
            FileMetadata.EventID == int(getattr(event, "EventID")),
            FileMetadata.GuestID == int(guest_cookie),
            FileMetadata.Deleted,
        )
        .first()
    )
    if not rec:
        return JSONResponse({"ok": False, "error": "Not found or not deleted."}, status_code=404)
    setattr(rec, "Deleted", False)
    db.commit()
    audit.info(
        "guest.upload.restore",
        extra={
            "event_id": int(getattr(event, "EventID")),
            "file_id": int(getattr(rec, "FileMetadataID")),
            "guest_id": int(guest_cookie),
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return JSONResponse({"ok": True})


@router.get("/guest/upload/{event_code}/list")
async def guest_list_files(
    request: Request,
    event_code: str,
    page: int = 1,
    size: int = PAGE_SIZE,
    type: str | None = None,
    sort: str | None = None,
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.Code == event_code).first()
    if not event:
        return JSONResponse({"ok": False, "error": "Invalid event."}, status_code=404)
    cookie_name = f"guest_session_{event.Code}"
    guest_cookie = request.cookies.get(cookie_name)
    if not guest_cookie:
        return JSONResponse({"ok": False, "error": "Not authorized."}, status_code=403)
    size = max(1, min(int(size or PAGE_SIZE), 100))
    page = max(1, int(page or 1))
    base_q = db.query(FileMetadata).filter(
        FileMetadata.EventID == int(getattr(event, "EventID")),
        FileMetadata.GuestID == int(guest_cookie),
        ~FileMetadata.Deleted,
    )
    media_type = (type or "").lower().strip()
    if media_type == "image":
        base_q = base_q.filter(FileMetadata.FileType.like("image%"))
    elif media_type == "video":
        base_q = base_q.filter(FileMetadata.FileType.like("video%"))
    total = base_q.count()

    sort_key = (sort or "newest").lower().strip()
    if sort_key == "oldest":
        order_clause = FileMetadata.UploadDate.asc()
    elif sort_key in ("name", "name_asc"):
        order_clause = FileMetadata.FileName.asc()
    elif sort_key in ("size", "size_desc"):
        order_clause = FileMetadata.FileSize.desc()
    elif sort_key == "size_asc":
        order_clause = FileMetadata.FileSize.asc()
    else:
        order_clause = FileMetadata.UploadDate.desc()

    files = base_q.order_by(order_clause).limit(size).offset((page - 1) * size).all()
    uid = int(getattr(event, "UserID"))
    eid = int(getattr(event, "EventID"))
    base = f"/storage/{uid}/{eid}/"
    items = []
    for f in files:
        size_b = int(getattr(f, "FileSize", 0) or 0)
        if size_b >= 1024 * 1024:
            size_label = f"{size_b/(1024*1024):.1f} MB"
        elif size_b >= 1024:
            size_label = f"{size_b/1024:.0f} KB"
        else:
            size_label = f"{size_b} B"
        dt = getattr(f, "UploadDate", None)
        try:
            uploaded_display = dt.strftime("%Y-%m-%d %H:%M") if dt else ""
        except Exception:
            uploaded_display = ""
        items.append(
            {
                "id": int(getattr(f, "FileMetadataID")),
                "name": getattr(f, "FileName"),
                "type": getattr(f, "FileType"),
                "url": base + getattr(f, "FileName"),
                "size": size_label,
                "uploaded": uploaded_display,
            }
        )
    has_more = (page * size) < total
    return JSONResponse({"ok": True, "items": items, "has_more": has_more, "page": page})
