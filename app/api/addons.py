import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.addons import AddonCatalog, EventAddonPurchase
from app.services.auth import require_user
from db import get_db

router = APIRouter()
log = logging.getLogger(__name__)

@router.get("/extras", response_class=HTMLResponse)
async def extras_marketplace(request: Request, db: Session = Depends(get_db)):
    addons = []
    try:
        rows = (
            db.query(AddonCatalog)
            .filter(AddonCatalog.IsActive == True)  # noqa: E712
            .order_by(AddonCatalog.PriceCents.asc())
            .all()
        )
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
                    # Placeholder image path; can be enhanced with a DB column later
                    "image": "/static/images/examples/corporate1.svg",
                }
            )
    except Exception:
        # If the table doesn't exist yet, just render an empty list
        log.warning("Extras query failed (likely missing table)", exc_info=True)
    return templates.TemplateResponse(
        request,
        "extras.html",
        context={"addons": addons, "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY},
    )


@router.get("/addons", response_class=HTMLResponse)
async def list_addons(request: Request, db: Session = Depends(get_db)):
    # Backward compatibility: redirect legacy /addons to /extras, preserving query string
    try:
        qs = ("?" + str(request.url.query)) if request.url.query else ""
    except Exception:
        qs = ""
    return RedirectResponse(url=f"/extras{qs}", status_code=307)


@router.post("/addons/checkout")
@router.post("/extras/checkout")
async def addons_checkout(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    data = await request.json()
    code = str(data.get("code") or "").strip().lower()
    qty = int(data.get("quantity") or 1)
    # Prefer event_code for privacy; fall back to event_id for back-compat
    event_code = str(data.get("event_code") or "").strip()
    event_id = None
    resolved_code = event_code or None
    if event_code:
        # Resolve code -> id
        try:
            from app.models.event import Event as _Evt

            eobj = db.query(_Evt).filter(_Evt.Code == event_code).first()
            if eobj:
                event_id = int(getattr(eobj, "EventID"))
                resolved_code = str(getattr(eobj, "Code"))
        except Exception:
            event_id = None
    if event_id is None:
        # Back-compat: accept numeric event_id and map to code for return URLs
        try:
            raw_id = data.get("event_id")
            event_id = int(raw_id) if raw_id is not None else None
        except Exception:
            event_id = None
        if event_id:
            try:
                from app.models.event import Event as _Evt

                eobj2 = db.query(_Evt).filter(_Evt.EventID == event_id).first()
                if eobj2:
                    resolved_code = str(getattr(eobj2, "Code"))
            except Exception:
                resolved_code = None
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
    # Carry event_code back to extras page if provided (or derived from event_id)
    suffix = ""
    try:
        if resolved_code:
            suffix = f"&event_code={resolved_code}"
    except Exception:
        suffix = ""
    success_url = f"{base}/extras?success=1{suffix}"
    cancel_url = f"{base}/extras?canceled=1{suffix}"
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
