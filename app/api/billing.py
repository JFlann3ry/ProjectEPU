import json
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.billing import PaymentLog, Purchase
from app.models.event_plan import EventPlan
from app.services.auth import get_current_user, require_admin, require_user
from app.services.email_utils import send_billing_email
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.get("/pricing", response_class=HTMLResponse)
async def list_plans(request: Request, db: Session = Depends(get_db)):
    # Local normalize to avoid hard dependency
    def _parse_features(raw):
        if isinstance(raw, dict):
            data = raw
        else:
            try:
                data = json.loads(raw or "{}")
                if not isinstance(data, dict):
                    data = {}
            except Exception:
                data = {}

        # Coerce values
        def _int(v):
            try:
                return max(0, int(v or 0))
            except Exception:
                return 0

        return {
            "max_events": _int(data.get("max_events")),
            "max_guests_per_event": _int(data.get("max_guests_per_event")),
            "max_zip_download_items": _int(data.get("max_zip_download_items")),
            "max_storage_per_event_mb": _int(data.get("max_storage_per_event_mb")),
            "branding": bool(data.get("branding")),
            "analytics": str(data.get("analytics") or ""),
            "priority_support": bool(data.get("priority_support")),
            "qr_enabled": bool(data.get("qr_enabled")),
            "upload_months": _int(data.get("upload_months")),
            "download_months": _int(data.get("download_months")),
        }

    rows = (
        db.query(EventPlan)
        .filter(EventPlan.IsActive)
        .order_by(EventPlan.PriceCents.asc())
        .all()
    )
    # Remove any non-real options like a legacy "Pro Event"
    def _is_visible_plan(p: EventPlan) -> bool:
        try:
            code = (getattr(p, "Code") or "").lower().strip()
            name = (getattr(p, "Name") or "").lower().strip()
            if code in ("pro", "pro_event", "proevent"):
                return False
            if "pro event" in name:
                return False
        except Exception:
            pass
        return True
    rows = [p for p in rows if _is_visible_plan(p)]
    plans = []
    for p in rows:
        pf = _parse_features(getattr(p, "Features"))
        features = []
        limits = {}
        # Summaries & capabilities
        # Always show core limits rows so the compare table populates
        features.append("active_events")
        features.append("guests_per_event")
        # Optional capabilities
        if pf.get("qr_enabled"):
            features.append("qr")
        if pf.get("branding"):
            features.append("branding")
        if pf.get("analytics"):
            features.append("analytics")
        if pf.get("max_zip_download_items", 0) > 0:
            features.append("zip")
        # Upload/Download windows
        if int(pf.get("upload_months", 0)) > 0:
            features.append("upload_window")
        if int(pf.get("download_months", 0)) > 0:
            features.append("download_window")
        # Limits
        me = int(pf.get("max_events", 0))
        limits["active_events"] = me if me > 0 else None
        mg = int(pf.get("max_guests_per_event", 0))
        limits["guests_per_event"] = mg
        limits["upload_months"] = int(pf.get("upload_months", 0))
        limits["download_months"] = int(pf.get("download_months", 0))
        plans.append(
            {
                "id": int(getattr(p, "PlanID")),
                "name": str(getattr(p, "Name")),
                "code": str(getattr(p, "Code")),
                "description": str(getattr(p, "Description") or ""),
                "features": features,
                "limits": limits,
                "price_cents": int(getattr(p, "PriceCents") or 0),
                "currency": (getattr(p, "Currency") or "gbp").lower(),
            }
        )
    # Extras (Add-ons) for display on pricing page
    extras = []
    try:
        from app.models.addons import AddonCatalog

        addon_rows = (
            db.query(AddonCatalog)
            .filter(AddonCatalog.IsActive == True)  # noqa: E712
            .order_by(AddonCatalog.PriceCents.asc())
            .all()
        )
        for a in addon_rows:
            extras.append(
                {
                    "code": str(getattr(a, "Code")),
                    "name": str(getattr(a, "Name")),
                    "description": str(getattr(a, "Description") or ""),
                    "price_cents": int(getattr(a, "PriceCents") or 0),
                    "currency": (getattr(a, "Currency") or "gbp").lower(),
                    "allow_qty": bool(getattr(a, "AllowQuantity", False)),
                }
            )
    except Exception:
        extras = []
    return templates.TemplateResponse(
        request,
        "pricing.html",
        context={
            "plans": plans,
            "extras": extras,
            "message": request.query_params.get("message"),
            "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )


@router.get("/billing", response_class=HTMLResponse)
async def billing_alias(request: Request, db: Session = Depends(get_db)):
    # Prefer the account billing summary; pricing remains at /pricing
    return RedirectResponse("/billing/summary", status_code=302)


@router.get("/billing/summary", response_class=HTMLResponse)
async def billing_summary(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    items = []
    try:
        rows = (
            db.query(Purchase, EventPlan)
            .join(EventPlan, Purchase.PlanID == EventPlan.PlanID)
            .filter(Purchase.UserID == int(getattr(user, "UserID")))
            .order_by(Purchase.CreatedAt.desc())
            .limit(25)
            .all()
        )
        for p, plan in rows:
            items.append(
                {
                    "id": int(getattr(p, "PurchaseID")),
                    "status": str(getattr(p, "Status")),
                    "amount": str(getattr(p, "Amount")) + " " + str(getattr(p, "Currency")),
                    "created": getattr(p, "CreatedAt"),
                    "plan_code": str(getattr(plan, "Code", "") or ""),
                    "plan_name": str(getattr(plan, "Name", "Plan") or "Plan"),
                    "session": str(getattr(p, "StripeSessionID", "") or ""),
                }
            )
    except Exception:
        items = []
    return templates.TemplateResponse(
        request,
        "billing_summary.html",
        context={
            "items": items,
            "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )


@router.get("/billing/purchase/{purchase_id}", response_class=HTMLResponse)
async def billing_purchase_details(
    request: Request, purchase_id: int, db: Session = Depends(get_db)
):
    """Show details for a single purchase with actions to download/email receipt."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")

    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()
    details = {
        "id": int(getattr(p, "PurchaseID")),
        "status": str(getattr(p, "Status")),
        "amount": str(getattr(p, "Amount")) + " " + str(getattr(p, "Currency")),
        "created": getattr(p, "CreatedAt"),
        "plan_code": str(getattr(plan, "Code", "")) if plan else "",
        "plan_name": str(getattr(plan, "Name", "Plan")) if plan else "Plan",
        "plan_desc": str(getattr(plan, "Description", "") or "") if plan else "",
        "session": str(getattr(p, "StripeSessionID", "") or ""),
    }
    return templates.TemplateResponse(
        request,
        "billing_purchase.html",
        context={
            "purchase": details,
            "sent": 1 if (request.query_params.get("sent") == "1") else 0,
            "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )


def _compose_receipt_text(p, plan, user_email: str) -> str:
    """Create a plain-text receipt body for download/email."""
    lines = [
        "EPU – Receipt",
        "----------------------------------------",
        f"Receipt #: {getattr(p, 'PurchaseID')}",
        f"Date: {getattr(p, 'CreatedAt')}",
        f"Status: {getattr(p, 'Status')}",
        "",
        "Billed To:",
        f"  {user_email or 'User'}",
        "",
        "Item:",
        f"  Plan: {getattr(plan, 'Name', 'Plan') if plan else 'Plan'}",
        f"  Code: {getattr(plan, 'Code', '') if plan else ''}",
        "",
        "Totals:",
        f"  Amount: {getattr(p, 'Amount')} {getattr(p, 'Currency')}",
        "",
        "Notes:",
        "  This is a receipt for your records. It is not a VAT invoice.",
        "  For questions, contact support via /contact.",
    ]
    return "\n".join(lines)


@router.get("/billing/purchase/{purchase_id}/receipt")
async def billing_purchase_receipt(
    request: Request, purchase_id: int, db: Session = Depends(get_db)
):
    """Return a downloadable plain-text receipt for the purchase."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")
    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()

    user_email = getattr(user, "Email", "")
    body = _compose_receipt_text(p, plan, user_email)
    filename = f"receipt-{getattr(p, 'PurchaseID')}.txt"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Cache-Control": "no-store",
    }
    return Response(content=body, media_type="text/plain; charset=utf-8", headers=headers)


@router.get("/billing/purchase/{purchase_id}/receipt.pdf")
async def billing_purchase_receipt_pdf(
    request: Request, purchase_id: int, db: Session = Depends(get_db)
):
    """Return a downloadable PDF receipt for the purchase."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")
    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()

    try:
        # Lazy import so environments without reportlab can still run most routes
        from app.services.pdf_utils import ReceiptPDF

        pdf = ReceiptPDF()
        created = getattr(p, "CreatedAt")
        if not isinstance(created, datetime):
            created = datetime.utcnow()
        amount = getattr(p, "Amount", 0)
        currency = str(getattr(p, "Currency", "GBP") or "GBP")
        body = pdf.build(
            receipt_no=int(getattr(p, "PurchaseID")),
            date=created,
            status=str(getattr(p, "Status", "")).lower(),
            billed_to=str(getattr(user, "Email", "") or "User"),
            plan_name=str(getattr(plan, "Name", "Plan")) if plan else "Plan",
            plan_code=str(getattr(plan, "Code", "")) if plan else "",
            description=str(getattr(plan, "Description", "") or "") if plan else "",
            amount=amount,
            currency=currency,
        )
    except Exception:
        # Fallback to text if PDF generation fails
        user_email = getattr(user, "Email", "")
        body_text = _compose_receipt_text(p, plan, user_email)
        filename = f"receipt-{getattr(p, 'PurchaseID')}.txt"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-store",
        }
        return Response(content=body_text, media_type="text/plain; charset=utf-8", headers=headers)

    filename = f"receipt-{getattr(p, 'PurchaseID')}.pdf"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Cache-Control": "no-store",
    }
    return Response(content=body, media_type="application/pdf", headers=headers)


@router.post("/billing/purchase/{purchase_id}/email-receipt")
async def billing_purchase_email_receipt(
    request: Request, purchase_id: int, db: Session = Depends(get_db)
):
    """Email a simple receipt to the user's email address."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")
    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()
    to_email = getattr(user, "Email", None)
    if not to_email:
        raise HTTPException(status_code=400, detail="No email on account")

    # Simple rate limit: max 1 receipt email per user per rolling hour
    try:
        cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_count = (
            db.query(PaymentLog)
            .filter(
                PaymentLog.UserID == int(getattr(user, "UserID")),
                PaymentLog.EventType == "email_receipt",
                PaymentLog.CreatedAt >= cutoff,
            )
            .count()
        )
        if recent_count >= 1:
            # Too many requests
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except HTTPException:
        raise
    except Exception:
        # On failure to check, continue without blocking
        pass

    body = _compose_receipt_text(p, plan, to_email)
    try:
        await send_billing_email(to_email, subject="Your receipt – EPU", body=body)
        # Log successful send for rate limiting
        try:
            payload = json.dumps({"purchase_id": int(getattr(p, "PurchaseID")), "to": to_email})
        except Exception:
            payload = None
        log = PaymentLog(
            UserID=int(getattr(user, "UserID")),
            EventType="email_receipt",
            Payload=payload,
        )
        db.add(log)
        db.commit()
    except Exception:
        # Don't expose error details to user; surface in logs if needed.
        pass
    pid = int(getattr(p, "PurchaseID"))
    return RedirectResponse(
        f"/billing/purchase/{pid}?sent=1",
        status_code=303,
    )


# Legacy route: permanently redirect old /plans URL to canonical /pricing
@router.get("/plans")
async def legacy_plans_redirect():
    return RedirectResponse("/pricing", status_code=301)


@router.post("/admin/seed-plans", response_class=PlainTextResponse)
async def admin_seed_plans(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    # Import and run seeder logic in-process
    from app.db_seed_plans import PLANS, upsert_plan

    for spec in PLANS:
        upsert_plan(db, spec)
    return PlainTextResponse(
        "Seeded/updated plans: " + ", ".join([p.get("Code", "") for p in PLANS])
    )


@router.get("/admin/plans", response_class=PlainTextResponse)
async def admin_list_plans(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    rows = db.query(EventPlan).order_by(EventPlan.PriceCents.asc()).all()
    lines = ["Plans:"]
    for p in rows:
        lines.append(
            f"#{getattr(p,'PlanID')} code={getattr(p,'Code')} "
            f"name={getattr(p,'Name')} price={getattr(p,'PriceCents')} "
            f"{getattr(p,'Currency')}"
        )
    return PlainTextResponse("\n".join(lines))


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: Request, db: Session = Depends(get_db), user=Depends(require_user)
):
    data = await request.json()
    code = (data.get("plan") or "").strip().lower()
    if not code:
        raise HTTPException(status_code=400, detail="Missing plan code")
    plan = db.query(EventPlan).filter(EventPlan.Code == code, EventPlan.IsActive).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # If the user has a pending purchase from the last 24 hours, resume it
    try:
        threshold = datetime.utcnow() - timedelta(hours=24)
        existing = (
            db.query(Purchase)
            .filter(
                Purchase.UserID == int(getattr(user, "UserID")),
                Purchase.Status == "pending",
                Purchase.CreatedAt >= threshold,
            )
            .order_by(Purchase.CreatedAt.desc())
            .first()
        )
    except Exception:
        existing = None

    if existing:
        # Only resume if the pending purchase matches the selected plan, price, and currency
        try:
            existing_amount_cents = int(
                (Decimal(str(getattr(existing, "Amount"))) * Decimal(100)).to_integral_value()
            )
        except Exception:
            existing_amount_cents = 0
        selected_amount_cents = int(getattr(plan, "PriceCents", 0) or 0)
        existing_currency = str(getattr(existing, "Currency", "gbp") or "gbp").lower()
        selected_currency = str(getattr(plan, "Currency", "gbp") or "gbp").lower()
        same_plan = int(getattr(existing, "PlanID") or 0) == int(getattr(plan, "PlanID") or 0)
        same_price = existing_amount_cents == selected_amount_cents
        same_currency = existing_currency == selected_currency

        if not (same_plan, same_price, same_currency) == (True, True, True):
            # Mismatch: cancel the old pending purchase and proceed to create a new one
            try:
                setattr(existing, "Status", "canceled")
                db.commit()
            except Exception:
                db.rollback()
        else:
            # Create a fresh Stripe session for the existing purchase and return it
            try:
                import stripe  # type: ignore
            except Exception:
                raise HTTPException(status_code=500, detail="Stripe SDK not available")
            if not settings.STRIPE_SECRET_KEY:
                raise HTTPException(status_code=500, detail="Stripe secret key not configured")
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Price from purchase (fallback to plan if needed)
            try:
                amount_decimal = Decimal(str(getattr(existing, "Amount")))
            except Exception:
                amount_decimal = Decimal(0)
            currency = str(getattr(existing, "Currency", "gbp") or "gbp").lower()
            amount_cents = int((amount_decimal * Decimal(100)).to_integral_value())
            if amount_cents <= 0:
                amount_cents = int(getattr(plan, "PriceCents", 0) or 0)
                if amount_cents <= 0:
                    raise HTTPException(status_code=400, detail="Invalid purchase amount")

            # Plan info (best-effort for display)
            resume_plan = (
                db.query(EventPlan)
                .filter(EventPlan.PlanID == getattr(existing, "PlanID", None))
                .first()
            )
            plan_name = str(getattr(resume_plan, "Name", "Plan")) if resume_plan else "Plan"
            plan_desc = (
                str(getattr(resume_plan, "Description", "") or "") if resume_plan else ""
            )
            plan_code = str(getattr(resume_plan, "Code", "")) if resume_plan else ""

            base = settings.BASE_URL.rstrip("/")
            pid = int(getattr(existing, "PurchaseID"))
            success_url = f"{base}/billing/purchase/{pid}?success=1"
            cancel_url = f"{base}/billing/purchase/{pid}?canceled=1"

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
                                    "name": plan_name,
                                    "description": plan_desc,
                                },
                                "unit_amount": amount_cents,
                            },
                            "quantity": 1,
                        }
                    ],
                    metadata={
                        "user_id": str(getattr(user, "UserID")),
                        "plan_id": str(getattr(resume_plan, "PlanID", "")) if resume_plan else "",
                        "plan_code": plan_code,
                        "purchase_id": str(getattr(existing, "PurchaseID")),
                    },
                )
            except Exception as e:
                audit.error(
                    "billing.checkout.resume_error",
                    extra={
                        "purchase_id": int(getattr(existing, "PurchaseID")),
                        "error": str(e),
                    },
                )
                raise HTTPException(status_code=500, detail="Failed to create checkout session")

            setattr(existing, "StripeSessionID", str(session.get("id")))
            db.commit()

            audit.info(
                "billing.checkout.session_resumed",
                extra={
                    "purchase_id": int(getattr(existing, "PurchaseID")),
                    "user_id": int(getattr(user, "UserID")),
                    "session_id": session.get("id"),
                },
            )
            return JSONResponse(
                {
                    "id": session.get("id"),
                    "purchase_id": int(getattr(existing, "PurchaseID")),
                    "resumed": True,
                }
            )

    # Expire any stale pending purchases (>24h)
    try:
        stale_cutoff = datetime.utcnow() - timedelta(hours=24)
        stale_rows = (
            db.query(Purchase)
            .filter(
                Purchase.UserID == int(getattr(user, "UserID")),
                Purchase.Status == "pending",
                Purchase.CreatedAt < stale_cutoff,
            )
            .all()
        )
        for sp in stale_rows:
            setattr(sp, "Status", "canceled")
        if stale_rows:
            db.commit()
    except Exception:
        pass
    # Initialize Stripe
    try:
        import stripe  # type: ignore
    except Exception:
        raise HTTPException(status_code=500, detail="Stripe SDK not available")
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Extract safe primitives from ORM object for Stripe
    currency = str(getattr(plan, "Currency", "gbp") or "gbp").lower()
    amount_cents = int(getattr(plan, "PriceCents", 0) or 0)
    plan_name = str(getattr(plan, "Name", "Plan"))
    plan_desc = str(getattr(plan, "Description", "") or "")
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Plan price invalid")

    success_url = f"{settings.BASE_URL.rstrip('/')}/billing/summary?success=1"
    cancel_url = f"{settings.BASE_URL.rstrip('/')}/billing/summary?canceled=1"

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
                            "name": plan_name,
                            "description": plan_desc,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "user_id": str(user.UserID),
                "plan_id": str(getattr(plan, "PlanID", "")),
                "plan_code": str(getattr(plan, "Code", "")),
            },
        )
    except Exception as e:
        audit.error("billing.checkout.session_error", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

    # Record pending purchase
    amount_decimal = Decimal(amount_cents) / Decimal(100)
    purchase = Purchase(
        UserID=int(getattr(user, "UserID")),
        PlanID=int(getattr(plan, "PlanID")),
        Amount=amount_decimal,
        Currency=currency.upper(),
        StripeSessionID=str(session.get("id")),
        Status="pending",
    )
    db.add(purchase)
    db.commit()

    audit.info(
        "billing.checkout.session_created",
        extra={
            "user_id": int(getattr(user, "UserID")),
            "plan": str(getattr(plan, "Code", "")),
            "session_id": session.get("id"),
        },
    )
    return JSONResponse({"id": session.get("id")})


@router.post("/billing/purchase/{purchase_id}/restart-checkout")
async def restart_checkout_session(
    request: Request, purchase_id: int, db: Session = Depends(get_db), user=Depends(require_user)
):
    """Create a fresh Stripe Checkout session for an existing pending purchase.

    This resolves cases where the original session expired by generating a new session
    and updating the purchase's StripeSessionID, then returning the new session id.
    """
    # Load purchase and verify ownership
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")
    status = str(getattr(p, "Status", "")).lower()
    if status in {"paid", "refunded", "canceled", "cancelled"}:
        raise HTTPException(status_code=400, detail="Purchase is not payable")

    # Fetch plan info for display/metadata
    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()
    plan_name = str(getattr(plan, "Name", "Plan")) if plan else "Plan"
    plan_desc = str(getattr(plan, "Description", "") or "") if plan else ""
    plan_code = str(getattr(plan, "Code", "")) if plan else ""

    # Determine price from stored purchase amount/currency
    try:
        amount_decimal = Decimal(str(getattr(p, "Amount")))
    except Exception:
        amount_decimal = Decimal(0)
    currency = str(getattr(p, "Currency", "gbp") or "gbp").lower()
    amount_cents = int((amount_decimal * Decimal(100)).to_integral_value())
    if amount_cents <= 0:
        # Fallback to plan price if stored amount is invalid
        amount_cents = int(getattr(plan, "PriceCents", 0) or 0) if plan else 0
        if amount_cents <= 0:
            raise HTTPException(status_code=400, detail="Invalid purchase amount")

    # Initialize Stripe
    try:
        import stripe  # type: ignore
    except Exception:
        raise HTTPException(status_code=500, detail="Stripe SDK not available")
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY

    base = settings.BASE_URL.rstrip("/")
    pid = int(getattr(p, "PurchaseID"))
    success_url = f"{base}/billing/purchase/{pid}?success=1"
    cancel_url = f"{base}/billing/purchase/{pid}?canceled=1"

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
                            "name": plan_name,
                            "description": plan_desc,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "user_id": str(getattr(user, "UserID")),
                "plan_id": str(getattr(plan, "PlanID", "")) if plan else "",
                "plan_code": plan_code,
                "purchase_id": str(getattr(p, "PurchaseID")),
            },
        )
    except Exception as e:
        audit.error(
            "billing.checkout.restart_error",
            extra={"purchase_id": int(getattr(p, "PurchaseID")), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

    # Update purchase with new session id and keep status pending
    setattr(p, "StripeSessionID", str(session.get("id")))
    db.commit()

    audit.info(
        "billing.checkout.session_restarted",
        extra={
            "purchase_id": int(getattr(p, "PurchaseID")),
            "user_id": int(getattr(user, "UserID")),
            "session_id": session.get("id"),
        },
    )
    return JSONResponse({"id": session.get("id")})


@router.get("/billing/purchase/{purchase_id}/pay")
async def pay_purchase_redirect(
    request: Request,
    purchase_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Server-side start of checkout: create a fresh session and 303 redirect to Stripe.

    Useful when a previously shared Stripe link expired; this stable URL will
    always generate a new session for the pending purchase.
    """
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")
    status = str(getattr(p, "Status", "")).lower()
    if status in {"paid", "refunded", "canceled", "cancelled"}:
        raise HTTPException(status_code=400, detail="Purchase is not payable")

    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()
    plan_name = str(getattr(plan, "Name", "Plan")) if plan else "Plan"
    plan_desc = str(getattr(plan, "Description", "") or "") if plan else ""

    try:
        amount_decimal = Decimal(str(getattr(p, "Amount")))
    except Exception:
        amount_decimal = Decimal(0)
    currency = str(getattr(p, "Currency", "gbp") or "gbp").lower()
    amount_cents = int((amount_decimal * Decimal(100)).to_integral_value())
    if amount_cents <= 0:
        amount_cents = int(getattr(plan, "PriceCents", 0) or 0) if plan else 0
        if amount_cents <= 0:
            raise HTTPException(status_code=400, detail="Invalid purchase amount")

    try:
        import stripe  # type: ignore
    except Exception:
        raise HTTPException(status_code=500, detail="Stripe SDK not available")
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY

    base = settings.BASE_URL.rstrip("/")
    pid = int(getattr(p, "PurchaseID"))
    success_url = f"{base}/billing/purchase/{pid}?success=1"
    cancel_url = f"{base}/billing/purchase/{pid}?canceled=1"

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
                            "name": plan_name,
                            "description": plan_desc,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "user_id": str(getattr(user, "UserID")),
                "plan_id": str(getattr(plan, "PlanID", "")) if plan else "",
                "plan_code": str(getattr(plan, "Code", "")) if plan else "",
                "purchase_id": str(getattr(p, "PurchaseID")),
            },
        )
    except Exception as e:
        audit.error(
            "billing.checkout.redirect_error",
            extra={"purchase_id": int(getattr(p, "PurchaseID")), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

    # Persist new session id for tracking
    setattr(p, "StripeSessionID", str(session.get("id")))
    db.commit()

    url = session.get("url")
    if not url:
        # Fallback to client flow if url is unavailable (older API)
        return JSONResponse({"id": session.get("id")})

    audit.info(
        "billing.checkout.redirect_started",
        extra={
            "purchase_id": int(getattr(p, "PurchaseID")),
            "user_id": int(getattr(user, "UserID")),
            "session_id": session.get("id"),
        },
    )
    return RedirectResponse(url, status_code=303)


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = None
    try:
        import stripe  # type: ignore

        stripe.api_key = settings.STRIPE_SECRET_KEY
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        if webhook_secret and sig_header:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = json.loads(payload.decode("utf-8"))
    except Exception as e:
        # Log and return 400
        db.add(
            PaymentLog(
                UserID=None,
                EventType="webhook_error",
                Payload=payload.decode("utf-8"),
                ErrorMessage=str(e),
            )
        )
        db.commit()
        return PlainTextResponse("invalid", status_code=400)

    etype = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
    try:
        if etype == "checkout.session.completed":
            obj = (
                event.get("data", {}).get("object", {})
                if isinstance(event, dict)
                else event.data.object
            )
            session_id = obj.get("id") if isinstance(obj, dict) else getattr(obj, "id", None)
            payment_intent = (
                obj.get("payment_intent")
                if isinstance(obj, dict)
                else getattr(obj, "payment_intent", None)
            )
            purchase = db.query(Purchase).filter(Purchase.StripeSessionID == session_id).first()
            if purchase:
                setattr(purchase, "Status", "paid")
                if payment_intent:
                    setattr(purchase, "StripePaymentIntentID", str(payment_intent))
                db.commit()
                # Notify user best-effort
                try:
                    from app.models.user import User

                    u = (
                        db.query(User)
                        .filter(User.UserID == getattr(purchase, "UserID", None))
                        .first()
                    )
                    to_email = getattr(u, "Email", None) if u else None
                    if to_email:
                        await send_billing_email(
                            to_email,
                            subject="Payment received – EPU",
                            body="Thanks for your purchase. Your plan is now active.",
                        )
                except Exception:
                    pass
        elif etype == "payment_intent.succeeded":
            obj = (
                event.get("data", {}).get("object", {})
                if isinstance(event, dict)
                else event.data.object
            )
            pi_id = obj.get("id") if isinstance(obj, dict) else getattr(obj, "id", None)
            purchase = db.query(Purchase).filter(Purchase.StripePaymentIntentID == pi_id).first()
            if purchase:
                setattr(purchase, "Status", "paid")
                db.commit()
                try:
                    from app.models.user import User

                    u = (
                        db.query(User)
                        .filter(User.UserID == getattr(purchase, "UserID", None))
                        .first()
                    )
                    to_email = getattr(u, "Email", None) if u else None
                    if to_email:
                        await send_billing_email(
                            to_email,
                            subject="Payment succeeded – EPU",
                            body="Thanks for your purchase. Your plan is now active.",
                        )
                except Exception:
                    pass
        # Log event
        db.add(
            PaymentLog(
                UserID=None,
                EventType=str(etype or "unknown"),
                StripeEventID=(
                    event.get("id") if isinstance(event, dict) else getattr(event, "id", None)
                ),
                Payload=payload.decode("utf-8"),
            )
        )
        db.commit()
    except Exception as e:
        db.add(
            PaymentLog(
                UserID=None,
                EventType="handler_error",
                Payload=payload.decode("utf-8"),
                ErrorMessage=str(e),
            )
        )
        db.commit()
        return PlainTextResponse("error", status_code=500)

    return PlainTextResponse("ok", status_code=200)


@router.post("/admin/refund")
async def admin_refund(
    request: Request,
    purchase_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    # Find purchase
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p:
        raise HTTPException(status_code=404, detail="Purchase not found")
    # Load Stripe
    try:
        import stripe  # type: ignore

        stripe.api_key = settings.STRIPE_SECRET_KEY
    except Exception:
        raise HTTPException(status_code=500, detail="Stripe SDK not available")
    pi = getattr(p, "StripePaymentIntentID", None)
    if not pi:
        raise HTTPException(status_code=400, detail="No payment intent on purchase")
    try:
        stripe.Refund.create(
            payment_intent=pi, reason="requested_by_customer"
        )  # type: ignore
        setattr(p, "Status", "refunded")
        db.commit()
        # Notify user via email (best-effort)
        try:
            from app.models.user import User

            u = db.query(User).filter(User.UserID == getattr(p, "UserID", None)).first()
            to_email = getattr(u, "Email", None) if u else None
            if to_email:
                msg = (
                    "Your purchase #"
                    + str(getattr(p, 'PurchaseID'))
                    + " has been refunded. "
                    + (("Reason: " + reason) if reason else "")
                )
                await send_billing_email(
                    to_email,
                    subject="Refund processed – EPU",
                    body=msg,
                )
        except Exception:
            pass
        audit.info(
            "billing.refund.success",
            extra={
                "purchase_id": int(getattr(p, "PurchaseID")),
                "admin_id": int(getattr(user, "UserID")),
            },
        )
        return JSONResponse({"ok": True})
    except Exception as e:
        audit.error(
            "billing.refund.error",
            extra={"purchase_id": int(getattr(p, "PurchaseID")), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Refund failed")


@router.post("/admin/cancel")
async def admin_cancel(
    request: Request,
    purchase_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p:
        raise HTTPException(status_code=404, detail="Purchase not found")
    try:
        setattr(p, "Status", "canceled")
        db.commit()
        try:
            from app.models.user import User

            u = db.query(User).filter(User.UserID == getattr(p, "UserID", None)).first()
            to_email = getattr(u, "Email", None) if u else None
            if to_email:
                msg = (
                    "Your purchase #"
                    + str(getattr(p, 'PurchaseID'))
                    + " has been canceled. "
                    + (("Reason: " + reason) if reason else "")
                )
                await send_billing_email(
                    to_email,
                    subject="Subscription canceled – EPU",
                    body=msg,
                )
        except Exception:
            pass
        audit.info(
            "billing.cancel.success",
            extra={
                "purchase_id": int(getattr(p, "PurchaseID")),
                "admin_id": int(getattr(user, "UserID")),
            },
        )
        return JSONResponse({"ok": True})
    except Exception as e:
        audit.error(
            "billing.cancel.error",
            extra={"purchase_id": int(getattr(p, "PurchaseID")), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Cancel failed")


@router.get("/admin/billing", response_class=PlainTextResponse)
async def admin_billing_list(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    from app.models.billing import Purchase
    from app.models.event_plan import EventPlan

    rows = (
        db.query(Purchase, EventPlan)
        .join(EventPlan, Purchase.PlanID == EventPlan.PlanID)
        .order_by(Purchase.CreatedAt.desc())
        .limit(200)
        .all()
    )
    lines = ["Purchases (latest 200):"]
    for p, plan in rows:
        lines.append(
            f"#{getattr(p, 'PurchaseID')} user={getattr(p, 'UserID')} "
            f"plan={getattr(plan, 'Code')} status={getattr(p, 'Status')} "
            f"amount={getattr(p, 'Amount')} {getattr(p, 'Currency')}"
        )
    return PlainTextResponse("\n".join(lines))


@router.get("/admin/payment-logs", response_class=PlainTextResponse)
async def admin_payment_logs(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    from app.models.billing import PaymentLog

    logs = db.query(PaymentLog).order_by(PaymentLog.CreatedAt.desc()).limit(200).all()
    lines = ["Payment Logs (latest 200):"]
    for log in logs:
        lines.append(
            f"#{getattr(log, 'LogID')} type={getattr(log, 'EventType')} "
            f"err={getattr(log, 'ErrorMessage')}"
        )
    return PlainTextResponse("\n".join(lines))


@router.get("/admin/billing/manage", response_class=HTMLResponse)
async def admin_billing_manage(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    from app.models.billing import Purchase
    from app.models.event_plan import EventPlan
    from app.models.user import User

    rows = (
        db.query(Purchase, EventPlan, User)
        .join(EventPlan, Purchase.PlanID == EventPlan.PlanID)
        .join(User, Purchase.UserID == User.UserID)
        .order_by(Purchase.CreatedAt.desc())
        .limit(200)
        .all()
    )
    items = []
    for p, plan, u in rows:
        items.append(
            {
                "purchase_id": int(getattr(p, "PurchaseID")),
                "user_email": str(getattr(u, "Email") or ""),
                "plan": str(getattr(plan, "Code")),
                "amount": str(getattr(p, "Amount")) + " " + str(getattr(p, "Currency")),
                "status": str(getattr(p, "Status")),
                "created": getattr(p, "CreatedAt"),
            }
        )
    return templates.TemplateResponse(request, "admin_billing.html", context={"items": items})
