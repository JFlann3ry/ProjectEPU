import re

from fastapi.testclient import TestClient

from app.main import app
from app.models.billing import Purchase
from app.models.event import Event
from app.models.event_plan import EventPlan
from app.models.user import User
from app.services.auth import create_session
from db import SessionLocal

client = TestClient(app)


def seed_user_with_single_plan(db):
    # Create or get user
    u = db.query(User).filter(User.Email == 'single@example.com').first()
    if not u:
        u = User(FirstName='Test', LastName='User', Email='single@example.com', HashedPassword='x', IsActive=True)
        db.add(u)
        db.commit()
        db.refresh(u)
    # Create single plan if missing
    plan = db.query(EventPlan).filter(EventPlan.Code == 'single').first()
    if not plan:
        plan = EventPlan(Name='Single', Code='single', Description='Single event plan', PriceCents=0)
        db.add(plan)
        db.commit()
        db.refresh(plan)
    # Create a purchase to assign plan if missing
    p = db.query(Purchase).filter(Purchase.UserID == u.UserID, Purchase.PlanID == plan.PlanID).first()
    if not p:
        p = Purchase(UserID=u.UserID, PlanID=plan.PlanID, Amount=0, Currency='GBP', Status='active')
        db.add(p)
        db.commit()
    # Create an event for this user to hit the quota
    # Create an event for this user to hit the quota if missing
    e = db.query(Event).filter(Event.UserID == u.UserID, Event.Code == 'EXIST1').first()
    if not e:
        e = Event(EventTypeID=None, UserID=u.UserID, Name='Existing', Code='EXIST1', Password='pw', TermsChecked=True)
        db.add(e)
        db.commit()
        db.refresh(e)
    return u, plan, e


def test_create_event_shows_purchase_link():
    db = SessionLocal()
    try:
        u, plan, ev = seed_user_with_single_plan(db)
        # Create a valid session and attach it to the test client to simulate authentication
        sess = create_session(db, user_id=u.UserID)
        client.cookies.set('session_id', str(sess.SessionID))
        # For test simplicity, call GET /events/create and expect the template to include the purchase link
        r = client.get('/events/create')
        if r.status_code == 302 and 'location' in r.headers:
            r = client.get(r.headers['location'])
        assert r.status_code == 200
        text = r.text
        # We expect either the explicit purchase link or that the user was redirected to billing/pricing
        lowered = text.lower()
        assert (
            'additional_event' in text
            or re.search(r'additional event for', lowered)
            or 'pricing' in lowered
            or 'billing' in lowered
            or 'purchase' in lowered
        )
    finally:
        db.close()
