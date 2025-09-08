from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.addons import AddonCatalog, EventAddonPurchase
from app.services.auth import require_user
from db import get_db

router = APIRouter()


@router.get("/addons", response_class=HTMLResponse)
async def list_addons(request: Request, db: Session = Depends(get_db)):
    rows = (
        db.query(AddonCatalog)
        .filter(AddonCatalog.IsActive == True)  # noqa: E712
        .order_by(AddonCatalog.PriceCents.asc())
        .all()
    )
    addons = []
    for a in rows:
        addons.append(
            {
                "id": int(getattr(a, "AddonID")),
                "code": str(getattr(a, "Code")),
                "name": str(getattr(a, "Name")),
                "desc": str(getattr(a, "Description") or ""),
                "price_cents": int(getattr(a, "PriceCents") or 0),
                "currency": (getattr(a, "Currency") or "gbp").lower(),
                "allow_qty": bool(getattr(a, "AllowQuantity")),
                "min_qty": int(getattr(a, "MinQuantity") or 1),
                "max_qty": int(getattr(a, "MaxQuantity") or 1),
            }
        )
    return templates.TemplateResponse(
        request,
        "addons.html",
        context={"addons": addons, "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY},
    )


@router.post("/addons/checkout")
async def addons_checkout(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    data = await request.json()
    code = str(data.get("code") or "").strip().lower()
    qty = int(data.get("quantity") or 1)
    event_id = int(data.get("event_id") or 0) or None
    if not code:
        raise HTTPException(status_code=400, detail="Missing addon code")
    addon = (
        db.query(AddonCatalog)
        .filter(
            AddonCatalog.Code == code,
            AddonCatalog.IsActive == True,  # noqa: E712
        )
        .first()
    )
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    allow_qty = bool(getattr(addon, "AllowQuantity"))
    if not allow_qty:
        qty = 1
    qty = max(
        int(getattr(addon, "MinQuantity") or 1),
        min(qty, int(getattr(addon, "MaxQuantity") or 1)),
    )
    unit_cents = int(getattr(addon, "PriceCents") or 0)
    currency = str(getattr(addon, "Currency") or "gbp").lower()
    amount_cents = unit_cents * qty
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Addon price invalid; please contact support")

    # Create pending record
    amount_decimal = Decimal(amount_cents) / Decimal(100)
    p = EventAddonPurchase(
        UserID=int(getattr(user, "UserID")),
        EventID=event_id,
        AddonID=int(getattr(addon, "AddonID")),
        Quantity=qty,
        Amount=amount_decimal,
        Currency=currency.upper(),
        Status="pending",
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    # Stripe session
    try:
        import stripe  # type: ignore
    except Exception:
        raise HTTPException(status_code=500, detail="Stripe SDK not available")
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY

    base = settings.BASE_URL.rstrip("/")
    # Carry event_id back to addons page if provided
    suffix = ""
    try:
        if event_id:
            suffix = f"&event_id={int(event_id)}"
    except Exception:
        suffix = ""
    success_url = f"{base}/addons?success=1{suffix}"
    cancel_url = f"{base}/addons?canceled=1{suffix}"
    try:
        session = stripe.checkout.Session.create(  # type: ignore
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": str(getattr(addon, "Name")),
                            "description": str(getattr(addon, "Description") or ""),
                        },
                        "unit_amount": unit_cents,
                    },
                    "quantity": qty,
                }
            ],
            metadata={
                "user_id": str(getattr(user, "UserID")),
                "addon_id": str(getattr(addon, "AddonID")),
                "addon_code": str(getattr(addon, "Code")),
                "event_id": str(event_id or ""),
                "event_addon_purchase_id": str(getattr(p, "PurchaseID")),
            },
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

    setattr(p, "StripeSessionID", str(session.get("id")))
    db.commit()
    return JSONResponse({"id": session.get("id")})
