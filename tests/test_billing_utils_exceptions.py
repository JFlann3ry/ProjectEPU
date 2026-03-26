import logging
import sys
from types import SimpleNamespace

from sqlalchemy.exc import SQLAlchemyError

from app.services import billing_utils


class _PendingQuery:
    def __init__(self, pending):
        self._pending = pending

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._pending


class _PlanQuery:
    def __init__(self, plan):
        self._plan = plan

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._plan


class _FakeDB:
    def __init__(self, pending=None, plan=None, fail_plan_lookup=False):
        self.pending = pending or []
        self.plan = plan
        self.fail_plan_lookup = fail_plan_lookup
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Purchase":
            return _PendingQuery(self.pending)
        if self.fail_plan_lookup:
            raise SQLAlchemyError("plan lookup failed")
        return _PlanQuery(self.plan)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_reconcile_pending_with_stripe_logs_and_records_stripe_errors(monkeypatch, caplog):
    from app.core.settings import settings

    class FakeStripeError(Exception):
        pass

    class FakeStripe:
        api_key = None

        class error:
            StripeError = FakeStripeError

        class checkout:
            class Session:
                @staticmethod
                def retrieve(_sid):
                    raise FakeStripeError("stripe temporarily unavailable")

    purchase = SimpleNamespace(
        UserID=1,
        Status="pending",
        StripeSessionID="cs_test_123",
        StripePaymentIntentID=None,
    )
    db = _FakeDB(pending=[purchase])

    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test", raising=False)
    monkeypatch.setitem(sys.modules, "stripe", FakeStripe)

    with caplog.at_level(logging.WARNING, logger="billing"):
        billing_utils._reconcile_pending_with_stripe(db, user_id=1)

    assert "Stripe reconciliation failed" in caplog.text
    assert any(getattr(item, "EventType", "") == "reconcile_error" for item in db.added)


def test_provision_user_plan_logs_query_failure_without_raising(caplog):
    purchase = SimpleNamespace(UserID=7, PurchaseID=77, PlanID=3)
    db = _FakeDB(fail_plan_lookup=True)

    # Should not raise even when plan lookup fails
    with caplog.at_level(logging.WARNING, logger="billing"):
        billing_utils.provision_user_plan(db, purchase)

    # Key assertion: failure is logged but doesn't crash
    assert "plan lookup failed" in caplog.text
