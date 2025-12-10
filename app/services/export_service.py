import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.billing import PaymentLog, Purchase
from app.models.event import Event, FavoriteFile, FileMetadata, GuestMessage
from app.models.export import UserDataExportJob
from app.models.user import User
from app.models.user_prefs import UserEmailPreference


def _safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ("-", "_", "."))[:100]


def build_user_export_zip(db: Session, user: User, storage_root: str = "storage") -> dict:
    job = (
        db.query(UserDataExportJob)
        .filter(UserDataExportJob.UserID == user.UserID)
        .order_by(UserDataExportJob.JobID.desc())
        .first()
    )
    if not job:
        raise RuntimeError("No export job found")
    setattr(job, "Status", "running")
    db.commit()

    tmpdir = tempfile.mkdtemp(prefix="export_")
    try:
        # Collect data into JSON serializable dicts
        user_rec = {
            "UserID": user.UserID,
            "FirstName": user.FirstName,
            "LastName": user.LastName,
            "Email": user.Email,
            "DateCreated": str(user.DateCreated) if getattr(user, "DateCreated", None) else None,
            "LastUpdated": str(user.LastUpdated) if getattr(user, "LastUpdated", None) else None,
            "EmailVerified": bool(getattr(user, "EmailVerified", False)),
        }

        events = db.query(Event).filter(Event.UserID == user.UserID).all()
        events_data: List[Dict[str, Any]] = []
        files_data: List[Dict[str, Any]] = []
        favorites_data: List[Dict[str, Any]] = []
        messages_data: List[Dict[str, Any]] = []

        for ev in events:
            events_data.append(
                {
                    "EventID": ev.EventID,
                    "Name": ev.Name,
                    "Date": str(getattr(ev, "Date", None)) if getattr(ev, "Date", None) else None,
                    "Code": ev.Code,
                    "CreatedAt": (
                        str(getattr(ev, "CreatedAt", None))
                        if getattr(ev, "CreatedAt", None)
                        else None
                    ),
                    "Published": bool(getattr(ev, "Published", False)),
                }
            )
            # Files for this event
            fmeta = db.query(FileMetadata).filter(FileMetadata.EventID == ev.EventID).all()
            for f in fmeta:
                files_data.append(
                    {
                        "FileMetadataID": f.FileMetadataID,
                        "EventID": f.EventID,
                        "FileName": f.FileName,
                        "FileType": f.FileType,
                        "FileSize": f.FileSize,
                        "CapturedDateTime": (
                            str(getattr(f, "CapturedDateTime", None))
                            if getattr(f, "CapturedDateTime", None)
                            else None
                        ),
                        "GPSLat": f.GPSLat,
                        "GPSLong": f.GPSLong,
                        "Checksum": f.Checksum,
                        "UploadDate": (
                            str(getattr(f, "UploadDate", None))
                            if getattr(f, "UploadDate", None)
                            else None
                        ),
                        "Deleted": bool(getattr(f, "Deleted", False)),
                    }
                )

        # Favorites
        favs = db.query(FavoriteFile).filter(FavoriteFile.UserID == user.UserID).all()
        for fav in favs:
            favorites_data.append(
                {
                    "FavoriteID": fav.FavoriteID,
                    "FileMetadataID": fav.FileMetadataID,
                    "CreatedAt": (
                        str(getattr(fav, "CreatedAt", None))
                        if getattr(fav, "CreatedAt", None)
                        else None
                    ),
                }
            )

        # Guest Messages on user's events
        event_ids = [e.EventID for e in events]
        if event_ids:
            msgs = db.query(GuestMessage).filter(GuestMessage.EventID.in_(event_ids)).all()
            for m in msgs:
                messages_data.append(
                    {
                        "GuestMessageID": m.GuestMessageID,
                        "EventID": m.EventID,
                        "DisplayName": m.DisplayName,
                        "Message": m.Message,
                        "CreatedAt": (
                            str(getattr(m, "CreatedAt", None))
                            if getattr(m, "CreatedAt", None)
                            else None
                        ),
                        "Deleted": bool(getattr(m, "Deleted", False)),
                    }
                )

        # Email preferences
        prefs = (
            db.query(UserEmailPreference).filter(UserEmailPreference.UserID == user.UserID).first()
        )
        if prefs:
            prefs_data = {
                "MarketingOptIn": bool(getattr(prefs, "MarketingOptIn", False)),
                "ProductUpdatesOptIn": bool(getattr(prefs, "ProductUpdatesOptIn", False)),
                "EventRemindersOptIn": bool(getattr(prefs, "EventRemindersOptIn", False)),
                "UpdatedAt": (
                    str(getattr(prefs, "UpdatedAt", None))
                    if getattr(prefs, "UpdatedAt", None)
                    else None
                ),
            }
        else:
            prefs_data = None

        # Purchases and payment logs (user-related only)
        purchases = db.query(Purchase).filter(Purchase.UserID == user.UserID).all()
        purchases_data = []
        for p in purchases:
            amt = getattr(p, "Amount", None)
            purchases_data.append(
                {
                    "PurchaseID": p.PurchaseID,
                    "PlanID": p.PlanID,
                    "Amount": float(amt) if amt is not None else None,
                    "Currency": p.Currency,
                    "Status": p.Status,
                    "CreatedAt": (
                        str(getattr(p, "CreatedAt", None))
                        if getattr(p, "CreatedAt", None)
                        else None
                    ),
                }
            )

        paylogs = db.query(PaymentLog).filter(PaymentLog.UserID == user.UserID).all()
        payment_logs_data = []
        for pl in paylogs:
            payment_logs_data.append(
                {
                    "LogID": pl.LogID,
                    "EventType": pl.EventType,
                    "StripeEventID": pl.StripeEventID,
                    "CreatedAt": (
                        str(getattr(pl, "CreatedAt", None))
                        if getattr(pl, "CreatedAt", None)
                        else None
                    ),
                }
            )

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "user": user_rec,
            "events": events_data,
            "files": files_data,
            "favorites": favorites_data,
            "guest_messages": messages_data,
            "email_preferences": prefs_data,
            "purchases": purchases_data,
            "payment_logs": payment_logs_data,
        }

        # Write manifest
        manifest_path = os.path.join(tmpdir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        # Create zip
        out_name = (
            f"user_{user.UserID}_export_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        )
        out_name = _safe_filename(out_name) + ".zip"
        out_dir = os.path.join(storage_root, "exports", str(user.UserID))
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.abspath(os.path.join(out_dir, out_name))
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.write(manifest_path, arcname="manifest.json")

        # Update job
        setattr(job, "Status", "completed")
        # Store naive UTC for DB columns that are naive
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        setattr(job, "CompletedAt", now_utc)
        setattr(job, "ExpiresAt", now_utc + timedelta(days=7))
        setattr(job, "FilePath", out_path)
        db.commit()
        return {"ok": True, "path": out_path}
    except Exception as e:
        setattr(job, "Status", "failed")
        setattr(job, "ErrorMessage", str(e))
        db.commit()
        raise
    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
