from sqlalchemy.orm import Session

from app.models.addons import AddonCatalog
from db import SessionLocal

ADDONS = [
    {
        "Code": "extra_event",
        "Name": "Additional Event",
        "Description": "Add one more event to your account",
        "PriceCents": 1500,
        "Currency": "gbp",
        "AllowQuantity": True,
        "MinQuantity": 1,
        "MaxQuantity": 10,
    },
    {
        "Code": "live_gallery",
        "Name": "Live Gallery Link",
        "Description": "Live gallery link for displaying uploads in real-time",
        "PriceCents": 1000,
        "Currency": "gbp",
        "AllowQuantity": False,
        "MinQuantity": 1,
        "MaxQuantity": 1,
    },
    {
        "Code": "qr_cards",
        "Name": "QR Cards",
        "Description": "Printed cards with your event QR code (set of 50/100/200)",
        "PriceCents": 0,  # price determined by quantity option; handled at checkout
        "Currency": "gbp",
        "AllowQuantity": True,
        "MinQuantity": 50,
        "MaxQuantity": 500,
    },
    {
        "Code": "photo_prints",
        "Name": "Photo Printing",
        "Description": "Order physical prints of your favorite photos",
        "PriceCents": 0,
        "Currency": "gbp",
        "AllowQuantity": True,
        "MinQuantity": 10,
        "MaxQuantity": 500,
    },
]


def upsert_addon(db: Session, spec: dict):
    code = spec["Code"].lower()
    addon = db.query(AddonCatalog).filter(AddonCatalog.Code == code).first()
    if not addon:
        addon = AddonCatalog(Code=code)
        db.add(addon)
    for k, v in spec.items():
        if k == "Code":
            continue
        setattr(addon, k, v)
    setattr(addon, "IsActive", True)
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        for a in ADDONS:
            upsert_addon(db, a)
        print("Seeded addons: ", ", ".join([a["Code"] for a in ADDONS]))
    finally:
        db.close()
