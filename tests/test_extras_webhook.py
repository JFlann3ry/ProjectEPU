import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.mark.usefixtures("db_session")
def test_extras_webhook_marks_eventaddon_and_creates_entitlement(db_session):
    client = TestClient(app)
    db = db_session

    # Create addon and pending EventAddonPurchase tied to fake session id
    from app.models.addons import AddonCatalog, EventAddonPurchase
    from app.models.billing import PaymentLog

    # Create addon if missing (tests may run multiple times)
    addon = db.query(AddonCatalog).filter(AddonCatalog.Code == "additional_event").first()
    if not addon:
        addon = AddonCatalog(
            Code="additional_event",
            Name="Additional Event",
            Description="Extra event",
            PriceCents=2000,
            Currency="GBP",
            AllowQuantity=False,
            IsActive=True,
        )
        db.add(addon)
        db.commit()
        db.refresh(addon)

    # Ensure a user exists for FK
    from app.models.user import User

    user = db.query(User).filter(User.Email == "extras_test@example.com").first()
    if not user:
        user = User(
            FirstName="Extra",
            LastName="Tester",
            Email="extras_test@example.com",
            HashedPassword="x",
            IsActive=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    eap = EventAddonPurchase(
        UserID=user.UserID,
        EventID=None,
        AddonID=addon.AddonID,
        Quantity=1,
        Amount=20.00,
        Currency="GBP",
        Status="pending",
        StripeSessionID="sess_addon_1",
    )
    db.add(eap)
    db.commit()
    db.refresh(eap)

    event = {
        "id": "evt_addon_1",
        "type": "checkout.session.completed",
        "data": {"object": {"id": "sess_addon_1", "payment_intent": "pi_addon_1"}},
    }

    headers = {"content-type": "application/json"}
    r = client.post("/stripe/webhook", json=event, headers=headers)
    assert r.status_code == 200

    # Refresh eap
    eap2 = (
        db.query(EventAddonPurchase)
        .filter(EventAddonPurchase.PurchaseID == eap.PurchaseID)
        .first()
    )
    assert eap2 is not None
    assert eap2.Status == "paid"
    assert eap2.StripePaymentIntentID == "pi_addon_1"

    # Ensure a zero-amount Purchase entitlement exists for this user
    from app.models.billing import Purchase

    ent = (
        db.query(Purchase)
        .filter(
            Purchase.StripeSessionID == "sess_addon_1",
            Purchase.Amount == 0,
            Purchase.Status == "paid",
        )
        .first()
    )
    assert ent is not None
    assert ent.StripeSessionID == "sess_addon_1"

    # There should be a PaymentLog entry
    logs = db.query(PaymentLog).filter(PaymentLog.StripeEventID == "evt_addon_1").all()
    assert len(logs) >= 1
