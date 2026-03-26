import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.billing import Purchase
from app.models.event_plan import EventPlan
from app.services.auth import require_user
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


# Legacy route: permanently redirect old /plans URL to canonical /pricing
@router.get("/plans")
async def legacy_plans_redirect():
    return RedirectResponse("/pricing", status_code=301)


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
        threshold = datetime.now(timezone.utc) - timedelta(hours=24)
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
            plan_desc = str(getattr(resume_plan, "Description", "") or "") if resume_plan else ""
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
        stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
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
    # If the user is upgrading from a lower-priced plan, charge only the difference.
    try:
        # Determine user's latest paid plan price
        from app.models.billing import Purchase as _Purchase
        from app.models.event_plan import EventPlan as _EP

        latest_paid = (
            db.query(_Purchase, _EP)
            .join(_EP, _Purchase.PlanID == _EP.PlanID)
            .filter(_Purchase.UserID == int(getattr(user, "UserID")), _Purchase.Status == "paid")
            .order_by(_Purchase.CreatedAt.desc())
            .first()
        )
        if latest_paid and str(getattr(plan, "Code", "")).lower() == "ultimate":
            _, user_plan = latest_paid
            user_price_cents = int(getattr(user_plan, "PriceCents", 0) or 0)
            # Only reduce the amount if the existing plan is cheaper than the target.
            if user_price_cents < amount_cents:
                amount_cents = amount_cents - user_price_cents
    except Exception:
        # If anything goes wrong computing upgrade price, fall back to full price.
        pass
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
