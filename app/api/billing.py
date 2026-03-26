import asyncio
import json
import logging
import os
from collections.abc import Awaitable
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.billing_admin import router as billing_admin_router
from app.api.billing_checkout import router as billing_checkout_router
from app.api.billing_receipts import router as billing_receipts_router
from app.core.settings import settings
from app.core.templates import templates
from app.models.billing import PaymentLog, Purchase
from app.models.event_plan import EventPlan
from app.services.auth import get_current_user
from app.services.email_utils import send_billing_email
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


def _apply_read_uncommitted_hint(db: Session) -> None:
    """Apply an isolation-level hint for SQL Server webhook reads only."""
    dialect_name = ""
    try:
        bind = getattr(db, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = str(getattr(dialect, "name", "") or "").lower()
    except (AttributeError, TypeError, ValueError):
        dialect_name = ""

    # READ UNCOMMITTED syntax below is SQL Server specific.
    if dialect_name != "mssql":
        audit.debug(
            "[stripe_webhook] skipping isolation-level hint for dialect=%s",
            dialect_name or "unknown",
        )
        return

    try:
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
    except SQLAlchemyError:
        audit.debug(
            "[stripe_webhook] failed to apply READ UNCOMMITTED hint",
            exc_info=True,
        )


def _schedule_webhook_task(
    coro: Awaitable[object],
    *,
    label: str,
    user_id: int | None,
    reference: str | None,
) -> asyncio.Task:
    """Schedule webhook side effects and observe completion failures."""
    task = asyncio.create_task(coro)

    def _on_done(done_task: asyncio.Task) -> None:
        try:
            done_task.result()
        except Exception:
            audit.exception(
                "[stripe_webhook] background task failed label=%s user=%s ref=%s",
                label,
                user_id,
                reference,
            )

    task.add_done_callback(_on_done)
    return task


def _stripe_webhook_error_types(stripe_module: object) -> tuple[type[BaseException], ...]:
    """Return Stripe webhook-related exception types, when available."""
    candidates: list[type[BaseException]] = []
    try:
        err_mod = getattr(stripe_module, "error")
        for name in ("SignatureVerificationError", "StripeError"):
            err = getattr(err_mod, name, None)
            if isinstance(err, type) and issubclass(err, BaseException):
                candidates.append(err)
    except AttributeError:
        return ()
    # Keep order stable while removing duplicates.
    return tuple(dict.fromkeys(candidates))


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

    rows = db.query(EventPlan).filter(EventPlan.IsActive).order_by(EventPlan.PriceCents.asc()).all()

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
    # Determine current logged-in user and their active paid plan (if any).
    try:
        user = get_current_user(request, db)
    except Exception:
        user = None

    user_plan_code = None
    user_plan_price_cents = None
    try:
        if user:
            from app.models.billing import Purchase
            from app.models.event_plan import EventPlan as _EP

            latest_paid = (
                db.query(Purchase, _EP)
                .join(_EP, Purchase.PlanID == _EP.PlanID)
                .filter(Purchase.UserID == int(getattr(user, "UserID")), Purchase.Status == "paid")
                .order_by(Purchase.CreatedAt.desc())
                .first()
            )
            if latest_paid:
                _, ep = latest_paid
                user_plan_code = (getattr(ep, "Code", None) or "").lower()
                try:
                    user_plan_price_cents = int(getattr(ep, "PriceCents", 0) or 0)
                except Exception:
                    user_plan_price_cents = None
    except Exception:
        user_plan_code = None

    # Also fetch canonical prices for the Basic/Ultimate plans so the template can
    # show an upgrade difference when appropriate.
    basic_plan_price_cents = None
    ultimate_plan_price_cents = None
    try:
        basic_plan = db.query(EventPlan).filter(EventPlan.Code == "single").first()
        if basic_plan:
            basic_plan_price_cents = int(getattr(basic_plan, "PriceCents", 0) or 0)
    except Exception:
        basic_plan_price_cents = None
    try:
        ultimate_plan = db.query(EventPlan).filter(EventPlan.Code == "ultimate").first()
        if ultimate_plan:
            ultimate_plan_price_cents = int(getattr(ultimate_plan, "PriceCents", 0) or 0)
    except Exception:
        ultimate_plan_price_cents = None

    ultimate_upgrade_diff_cents = None
    try:
        if (
            user_plan_price_cents is not None
            and ultimate_plan_price_cents is not None
            and user_plan_price_cents < ultimate_plan_price_cents
        ):
            ultimate_upgrade_diff_cents = ultimate_plan_price_cents - user_plan_price_cents
    except Exception:
        ultimate_upgrade_diff_cents = None

    return templates.TemplateResponse(
        request,
        "pricing.html",
        context={
            "plans": plans,
            "extras": extras,
            "message": request.query_params.get("message"),
            "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
            "user": user,
            "user_plan_code": user_plan_code,
            "user_plan_price_cents": user_plan_price_cents,
            "basic_plan_price_cents": basic_plan_price_cents,
            "ultimate_plan_price_cents": ultimate_plan_price_cents,
            "ultimate_upgrade_diff_cents": ultimate_upgrade_diff_cents,
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


router.include_router(billing_checkout_router)


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    payload_text = payload.decode("utf-8", errors="replace")
    sig_header = request.headers.get("stripe-signature")
    event = None
    # Keep debug message length short by computing parts separately
    _payload_len = len(payload or b"")
    _has_sig = bool(sig_header)
    audit.debug("[stripe_webhook] received payload length=%s sig=%s", _payload_len, _has_sig)
    try:
        import stripe  # type: ignore

        stripe.api_key = settings.STRIPE_SECRET_KEY
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        stripe_errors = _stripe_webhook_error_types(stripe)
        if webhook_secret and sig_header:
            try:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            except stripe_errors as e:
                audit.warning(
                    "[stripe_webhook] signature verification failed sig=%s",
                    bool(sig_header),
                    exc_info=True,
                )
                db.add(
                    PaymentLog(
                        UserID=None,
                        EventType="webhook_error",
                        Payload=payload_text,
                        ErrorMessage=str(e),
                    )
                )
                try:
                    db.commit()
                except SQLAlchemyError:
                    db.rollback()
                return PlainTextResponse("invalid", status_code=400)
            except (ValueError, TypeError, AttributeError) as e:
                audit.warning(
                    "[stripe_webhook] malformed signed payload",
                    exc_info=True,
                )
                db.add(
                    PaymentLog(
                        UserID=None,
                        EventType="webhook_error",
                        Payload=payload_text,
                        ErrorMessage=str(e),
                    )
                )
                try:
                    db.commit()
                except SQLAlchemyError:
                    db.rollback()
                return PlainTextResponse("invalid", status_code=400)
        else:
            event = json.loads(payload_text)
    except ImportError as e:
        audit.exception("[stripe_webhook] Stripe SDK unavailable")
        db.add(
            PaymentLog(
                UserID=None,
                EventType="webhook_error",
                Payload=payload_text,
                ErrorMessage=str(e),
            )
        )
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        return PlainTextResponse("invalid", status_code=400)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as e:
        audit.warning("[stripe_webhook] payload parse failed", exc_info=True)
        db.add(
            PaymentLog(
                UserID=None,
                EventType="webhook_error",
                Payload=payload_text,
                ErrorMessage=str(e),
            )
        )
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        return PlainTextResponse("invalid", status_code=400)

    etype = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
    _ev_id = event.get("id") if isinstance(event, dict) else getattr(event, "id", None)
    audit.debug("[stripe_webhook] parsed event type=%s id=%s", etype, _ev_id)

    # Helper: in tests we wire the test session into db._TEST_SESSION; when the
    # webhook runs inside the same Session we should avoid calling full commit()
    # which will expire or detach instances unexpectedly. Instead use flush()
    # so changes are visible but the transaction stays under test control.
    def _safe_commit():
        from sqlalchemy.exc import SQLAlchemyError

        try:
            import db as dbmod

            if getattr(dbmod, "_TEST_SESSION", None) is db:
                try:
                    db.flush()
                except SQLAlchemyError:
                    # fallback to commit if flush fails
                    db.commit()
                return
        except (ImportError, AttributeError):
            pass
        db.commit()

    # In some environments tests may use long-lived transactions. When supported
    # by the backend, prefer non-blocking reads for webhook reconciliation.
    _apply_read_uncommitted_hint(db)
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
            # Also handle EventAddonPurchase rows created by /extras checkout
            try:
                from app.models.addons import AddonCatalog
                from app.models.addons import EventAddonPurchase as _EAP

                eap = db.query(_EAP).filter(_EAP.StripeSessionID == session_id).first()
                if eap:
                    audit.debug(
                        "[stripe_webhook] marking EventAddonPurchase %s as paid",
                        getattr(eap, "PurchaseID", None),
                    )
                    setattr(eap, "Status", "paid")
                    if payment_intent:
                        setattr(eap, "StripePaymentIntentID", str(payment_intent))
                    _safe_commit()
                    audit.debug(
                        "[stripe_webhook] committed EventAddonPurchase %s",
                        getattr(eap, "PurchaseID", None),
                    )
                    # If this addon is additional_event, create a zero-value
                    # Purchase record to represent entitlement.
                    try:
                        addon = (
                            db.query(AddonCatalog)
                            .filter(AddonCatalog.AddonID == getattr(eap, "AddonID"))
                            .first()
                        )
                        if addon and (
                            str(getattr(addon, "Code", "")).lower() == "additional_event"
                        ):
                            # Ensure we have a PlanID to satisfy DB NOT NULL / FK constraints.
                            # Create or reuse a zero-cost EventPlan reserved for entitlements.
                            try:
                                from app.models.event_plan import EventPlan as _EventPlan

                                entitlement_plan = (
                                    db.query(_EventPlan)
                                    .filter(_EventPlan.Code == "addon_entitlement")
                                    .first()
                                )
                                if not entitlement_plan:
                                    entitlement_plan = _EventPlan(
                                        Name="Addon Entitlement",
                                        Code="addon_entitlement",
                                        Description="Auto-created plan for addon entitlements",
                                        PriceCents=0,
                                        Currency="GBP",
                                        IsActive=False,
                                    )
                                    db.add(entitlement_plan)
                                    _safe_commit()
                                    # refresh to populate PlanID
                                    try:
                                        db.refresh(entitlement_plan)
                                    except SQLAlchemyError:
                                        pass
                                plan_id_val = getattr(entitlement_plan, "PlanID", None)
                            except (SQLAlchemyError, ImportError):
                                audit.exception(
                                    "[stripe_webhook] failed to resolve entitlement plan"
                                    " for session=%s",
                                    session_id,
                                )
                                plan_id_val = None

                            ent = Purchase(
                                UserID=getattr(eap, "UserID"),
                                PlanID=plan_id_val,
                                Amount=0,
                                Currency=getattr(eap, "Currency", "GBP"),
                                Status="paid",
                                StripeSessionID=session_id,
                            )
                            # Create entitlement inside a nested transaction (savepoint)
                            # so a failure here doesn't rollback the outer transaction
                            try:
                                with db.begin_nested():
                                    db.add(ent)
                                    _safe_commit()
                                user_id = getattr(eap, "UserID", None)
                                audit.debug(
                                    (
                                        "[stripe_webhook] created entitlement Purchase for "
                                        "user=%s session=%s"
                                    ),
                                    user_id,
                                    session_id,
                                )
                            except (SQLAlchemyError, AttributeError, TypeError, ValueError):
                                audit.exception(
                                    "[stripe_webhook] entitlement creation failed for session=%s",
                                    session_id,
                                )

                        # Also, if the EventAddonPurchase references an EventID, mark the event task
                        try:
                            from app.models.event import EventTask as _ET

                            try:
                                raw_eid = getattr(eap, "EventID", None)
                                ref_eid = int(raw_eid) if raw_eid is not None else None
                            except (ValueError, TypeError):
                                ref_eid = None

                            if ref_eid:
                                # Upsert EventTask for this user/event and key 'purchase_extras'
                                try:
                                    et = (
                                        db.query(_ET)
                                        .filter(
                                            _ET.EventID == ref_eid,
                                            _ET.UserID == getattr(eap, "UserID"),
                                            _ET.Key == "purchase_extras",
                                        )
                                        .first()
                                    )
                                    if not et:
                                        et = _ET(
                                            EventID=ref_eid,
                                            UserID=getattr(eap, "UserID"),
                                            Key="purchase_extras",
                                            State="done",
                                            CompletedAt=datetime.now(timezone.utc).replace(
                                                tzinfo=None
                                            ),
                                        )
                                        db.add(et)
                                    else:
                                        setattr(et, "State", "done")
                                        setattr(
                                            et,
                                            "CompletedAt",
                                            datetime.now(timezone.utc).replace(tzinfo=None),
                                        )
                                    # save in nested transaction to avoid rolling back outer
                                    with db.begin_nested():
                                        _safe_commit()
                                except (
                                    SQLAlchemyError,
                                    AttributeError,
                                    TypeError,
                                    ValueError,
                                ):
                                    audit.exception(
                                        (
                                            "[stripe_webhook] failed to upsert EventTask for addon "
                                            "entitlement session=%s"
                                        ),
                                        session_id,
                                    )
                        except (ImportError, AttributeError):
                            audit.debug(
                                "[stripe_webhook] EventTask import/attr error session=%s",
                                session_id,
                            )
                    except (SQLAlchemyError, ImportError):
                        audit.exception(
                            "[stripe_webhook] addon lookup failed for EventAddonPurchase %s",
                            getattr(eap, "PurchaseID", None),
                        )
            except (SQLAlchemyError, ImportError):
                audit.exception("[stripe_webhook] EAP processing failed session=%s", session_id)
            purchase = db.query(Purchase).filter(Purchase.StripeSessionID == session_id).first()
            if purchase:
                setattr(purchase, "Status", "paid")
                if payment_intent:
                    setattr(purchase, "StripePaymentIntentID", str(payment_intent))
                _safe_commit()
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
                        try:
                            _schedule_webhook_task(
                                send_billing_email(
                                    to_email,
                                    subject="Payment received – EPU",
                                    body="Thanks for your purchase. Your plan is now active.",
                                ),
                                label="payment_received_email",
                                user_id=getattr(purchase, "UserID", None),
                                reference=str(session_id) if session_id else None,
                            )
                            audit.debug(
                                "[stripe_webhook] scheduled payment received email for user=%s",
                                getattr(purchase, "UserID", None),
                            )
                        except (RuntimeError, AttributeError):
                            audit.exception("[stripe_webhook] failed to schedule payment email")
                except (SQLAlchemyError, ImportError, AttributeError):
                    audit.debug("[stripe_webhook] user email lookup failed session=%s", session_id)
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
                _safe_commit()
                try:
                    from app.models.user import User

                    u = (
                        db.query(User)
                        .filter(User.UserID == getattr(purchase, "UserID", None))
                        .first()
                    )
                    to_email = getattr(u, "Email", None) if u else None
                    if to_email:
                        try:
                            _schedule_webhook_task(
                                send_billing_email(
                                    to_email,
                                    subject="Payment succeeded – EPU",
                                    body="Thanks for your purchase. Your plan is now active.",
                                ),
                                label="payment_succeeded_email",
                                user_id=getattr(purchase, "UserID", None),
                                reference=str(pi_id) if pi_id else None,
                            )
                            audit.debug(
                                "[stripe_webhook] scheduled payment succeeded email for user=%s",
                                getattr(purchase, "UserID", None),
                            )
                        except (RuntimeError, AttributeError):
                            audit.exception("[stripe_webhook] failed to schedule succeeded email")
                except (SQLAlchemyError, ImportError, AttributeError):
                    audit.debug("[stripe_webhook] user email lookup failed pi=%s", pi_id)
        # Log event: avoid duplicate logs for the same StripeEventID
        try:
            sid = event.get("id") if isinstance(event, dict) else getattr(event, "id", None)
            existing_log = None
            if sid:
                existing_log = db.query(PaymentLog).filter(PaymentLog.StripeEventID == sid).first()
            if not existing_log:
                db.add(
                    PaymentLog(
                        UserID=None,
                        EventType=str(etype or "unknown"),
                        StripeEventID=sid,
                        Payload=payload.decode("utf-8"),
                    )
                )
                _safe_commit()
        except SQLAlchemyError:
            # If logging check fails, still attempt to add a log to not lose diagnostics
            try:
                db.add(
                    PaymentLog(
                        UserID=None,
                        EventType=str(etype or "unknown"),
                        StripeEventID=(
                            event.get("id")
                            if isinstance(event, dict)
                            else getattr(event, "id", None)
                        ),
                        Payload=payload_text,
                    )
                )
                _safe_commit()
            except (SQLAlchemyError, AttributeError, TypeError, ValueError):
                audit.exception(
                    "[stripe_webhook] failed to persist fallback payment log event=%s",
                    (event.get("id") if isinstance(event, dict) else getattr(event, "id", None)),
                )
    except (SQLAlchemyError, AttributeError, TypeError, ValueError, RuntimeError) as e:
        sid = event.get("id") if isinstance(event, dict) else getattr(event, "id", None)
        audit.exception("[stripe_webhook] handler error event=%s type=%s", sid, etype)
        db.add(
            PaymentLog(
                UserID=None,
                EventType="handler_error",
                Payload=payload_text,
                ErrorMessage=str(e),
            )
        )
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        return PlainTextResponse("error", status_code=500)

    return PlainTextResponse("ok", status_code=200)


router.include_router(billing_admin_router)
router.include_router(billing_receipts_router)
