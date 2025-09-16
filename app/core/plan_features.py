# plan_features.py

from datetime import datetime, timedelta, timezone

# Feature matrix for each plan
PLAN_FEATURES = {
    "free": {
        "can_create_event": False,
        "can_upload": False,
        "can_view_gallery": False,
        "can_use_guestbook": False,
        "can_customize_qr": False,
        "can_customize_upload_page": False,
        "can_choose_theme": False,
        "upload_window_months": 0,
        "download_window_months": 0,
    },
    "basic": {
        "can_create_event": True,
        "can_upload": True,
        "can_view_gallery": True,
        "can_use_guestbook": True,
        "can_customize_qr": True,
        "can_customize_upload_page": "preset",
        "can_choose_theme": True,
        "upload_window_months": 2,
        "download_window_months": 12,
    },
    "ultimate": {
        "can_create_event": True,
        "can_upload": True,
        "can_view_gallery": True,
        "can_use_guestbook": True,
        "can_customize_qr": True,
        "can_customize_upload_page": "full",
        "can_choose_theme": True,
        "upload_window_months": 12,
        "download_window_months": 12,
    },
}

def has_feature(user, feature: str) -> bool:
    plan = getattr(user, "plan", "free")
    features = PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
    return bool(features.get(feature, False))

def upload_window_active(user, event_created_at: datetime) -> bool:
    plan = getattr(user, "plan", "free")
    months = PLAN_FEATURES[plan]["upload_window_months"]
    if not months:
        return False
    return datetime.now(timezone.utc) <= event_created_at + timedelta(days=30*months)

def download_window_active(user, event_created_at: datetime) -> bool:
    plan = getattr(user, "plan", "free")
    months = PLAN_FEATURES[plan]["download_window_months"]
    if not months:
        return False
    return datetime.now(timezone.utc) <= event_created_at + timedelta(days=30*months)
