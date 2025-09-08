import json

from sqlalchemy.orm import Session

from app.models.event_plan import EventPlan
from db import SessionLocal

PLANS = [
    # Free plan (no checkout); for sign-up and preview only
    {
        "Code": "free",
        "Name": "Free",
        "Description": "Create an account and preview an example event",
        "PriceCents": 0,
        "Currency": "gbp",
        "Features": {
            "max_events": 0,  # 0 = unlimited (no creation allowed without purchase; acts as base)
            "max_guests_per_event": 0,
            "max_zip_download_items": 0,
            "max_storage_per_event_mb": 0,
            "branding": False,
            "analytics": "",
            "priority_support": False,
            "qr_enabled": False,
            "upload_months": 0,
            "download_months": 0,
        },
    },
    # Basic plan (£25): 1 event, themed guest upload page, 2 mo upload window, 12 mo download
    {
        "Code": "single",
        "Name": "Basic",
        "Description": (
            "1 event, gallery of guest uploads, 2 mo upload, 12 mo download, "
            "themed upload page"
        ),
        "PriceCents": 2500,
        "Currency": "gbp",
        "Features": {
            "max_events": 1,
            "max_guests_per_event": 0,  # unlimited guests
            "max_zip_download_items": 0,
            "max_storage_per_event_mb": 0,
            "branding": True,  # choose from themes
            "analytics": "",
            "priority_support": False,
            "qr_enabled": True,
            "upload_months": 2,
            "download_months": 12,
        },
    },
    # Ultimate plan (£40): 12 mo upload & download, full customization of guest upload page
    {
        "Code": "ultimate",
        "Name": "Ultimate",
        "Description": (
            "12 mo upload & download from event date, customize upload page to "
            "match your theme"
        ),
        "PriceCents": 4000,
        "Currency": "gbp",
        "Features": {
            "max_events": 0,  # unlimited
            "max_guests_per_event": 0,  # unlimited guests
            "max_zip_download_items": 0,
            "max_storage_per_event_mb": 0,
            "branding": True,
            "analytics": "",
            "priority_support": False,
            "qr_enabled": True,
            "upload_months": 12,
            "download_months": 12,
        },
    },
]


def upsert_plan(db: Session, spec: dict):
    code = spec["Code"].lower()
    plan = db.query(EventPlan).filter(EventPlan.Code == code).first()
    if not plan:
        plan = EventPlan(Code=code)
        db.add(plan)
    setattr(plan, "Name", spec["Name"])  # type: ignore[arg-type]
    setattr(plan, "Description", spec.get("Description"))
    setattr(plan, "PriceCents", int(spec["PriceCents"]))
    setattr(plan, "Currency", spec.get("Currency", "usd"))
    setattr(plan, "Features", json.dumps(spec.get("Features", {})))
    setattr(plan, "IsActive", True)
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        for p in PLANS:
            upsert_plan(db, p)
        print("Seeded plans: ", ", ".join([p["Code"] for p in PLANS]))
    finally:
        db.close()
