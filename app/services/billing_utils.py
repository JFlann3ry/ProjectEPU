from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session


def get_active_plan(db: Session, user_id: int) -> Tuple[Optional[Any], Dict[str, Any]]:
    """Return (plan_row, features_dict) for the user's most recent paid plan.

    If none, returns (None, {}). Features is JSON-parsed, defaults to {}.
    """
    from app.models.billing import Purchase
    from app.models.event_plan import EventPlan

    plan = None
    features: Dict[str, Any] = {}
    try:
        latest = (
            db.query(Purchase, EventPlan)
            .join(EventPlan, Purchase.PlanID == EventPlan.PlanID)
            .filter(
                Purchase.UserID == user_id, Purchase.Status == "paid", EventPlan.IsActive
            )
            .order_by(Purchase.CreatedAt.desc())
            .first()
        )
        if latest:
            plan = latest[1]
            raw = getattr(plan, "Features", None) or "{}"
            try:
                features = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except Exception:
                features = {}
    except Exception:
        plan = None
        features = {}
    return plan, features
