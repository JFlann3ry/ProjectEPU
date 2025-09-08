from __future__ import annotations

from typing import Any, Dict, Tuple, TypedDict


class PlanFeatures(TypedDict, total=False):
    max_events: int  # 0 = unlimited
    max_guests_per_event: int
    max_zip_download_items: int
    max_storage_per_event_mb: int
    branding: bool
    analytics: str
    priority_support: bool
    qr_enabled: bool
    upload_months: int
    download_months: int


DEFAULTS: PlanFeatures = {
    "max_events": 0,
    "max_guests_per_event": 0,
    "max_zip_download_items": 0,
    "max_storage_per_event_mb": 0,
    "branding": False,
    "analytics": "",
    "priority_support": False,
    "qr_enabled": False,
    "upload_months": 0,
    "download_months": 0,
}


def parse_plan_features(raw: Any) -> PlanFeatures:
    """Normalize arbitrary JSON (dict/str/None) into a typed features dict with defaults."""
    features: Dict[str, Any]
    if isinstance(raw, dict):
        features = raw
    elif isinstance(raw, str):
        import json

        try:
            parsed = json.loads(raw)
            features = parsed if isinstance(parsed, dict) else {}
        except Exception:
            features = {}
    else:
        features = {}
    out: PlanFeatures = DEFAULTS.copy()  # type: ignore[assignment]
    # ints
    for k in (
        "max_events",
        "max_guests_per_event",
        "max_zip_download_items",
        "max_storage_per_event_mb",
    "upload_months",
    "download_months",
    ):
        try:
            v = int(features.get(k)) if features.get(k) is not None else DEFAULTS[k]  # type: ignore[index]
            if v < 0:
                v = 0
            out[k] = v  # type: ignore[index]
        except Exception:
            out[k] = DEFAULTS[k]  # type: ignore[index]
    # bools
    for k in ("branding", "priority_support", "qr_enabled"):
        try:
            out[k] = bool(features.get(k))  # type: ignore[index]
        except Exception:
            out[k] = DEFAULTS[k]  # type: ignore[index]
    # strings
    try:
        out["analytics"] = str(features.get("analytics") or DEFAULTS.get("analytics", ""))
    except Exception:
        out["analytics"] = ""
    return out


def can_create_event(current_events: int, features: PlanFeatures) -> Tuple[bool, str | None]:
    cap = int(features.get("max_events", 0))
    if cap == 0:
        return True, None
    if current_events < cap:
        return True, None
    return False, f"Event limit reached ({current_events}/{cap})."


def guest_cap_info(current_guests: int, features: PlanFeatures) -> Tuple[int, bool, float]:
    """Return (limit, is_capped, utilization_ratio). 0 limit means unlimited."""
    limit = int(features.get("max_guests_per_event", 0))
    if limit == 0:
        return 0, False, 0.0
    is_capped = current_guests >= limit
    ratio = (current_guests / limit) if limit > 0 else 0.0
    return limit, is_capped, ratio
