from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core import plan_features


def _freeze_now(monkeypatch, frozen_now: datetime) -> None:
    class _FrozenDateTime:
        @staticmethod
        def now(tz=None):
            if tz is None:
                return frozen_now
            return frozen_now.astimezone(tz)

    monkeypatch.setattr(plan_features, "datetime", _FrozenDateTime)


@pytest.mark.parametrize(
    "plan,delta_days,expected",
    [
        ("free", 1, False),
        ("basic", 59, True),
        ("basic", 60, True),
        ("basic", 61, False),
        ("ultimate", 359, True),
        ("ultimate", 360, True),
        ("ultimate", 361, False),
    ],
)
def test_upload_window_active_boundaries(monkeypatch, plan, delta_days, expected):
    frozen_now = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)
    _freeze_now(monkeypatch, frozen_now)

    user = SimpleNamespace(plan=plan)
    created_at = frozen_now - timedelta(days=delta_days)

    assert plan_features.upload_window_active(user, created_at) is expected


@pytest.mark.parametrize(
    "plan,delta_days,expected",
    [
        ("free", 1, False),
        ("basic", 359, True),
        ("basic", 360, True),
        ("basic", 361, False),
        ("ultimate", 359, True),
        ("ultimate", 360, True),
        ("ultimate", 361, False),
    ],
)
def test_download_window_active_boundaries(monkeypatch, plan, delta_days, expected):
    frozen_now = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)
    _freeze_now(monkeypatch, frozen_now)

    user = SimpleNamespace(plan=plan)
    created_at = frozen_now - timedelta(days=delta_days)

    assert plan_features.download_window_active(user, created_at) is expected


def test_upload_window_negative_expired_path(monkeypatch):
    frozen_now = datetime(2026, 3, 26, 12, 0, 1, tzinfo=timezone.utc)
    _freeze_now(monkeypatch, frozen_now)

    user = SimpleNamespace(plan="basic")
    created_at = frozen_now - timedelta(days=60, seconds=1)

    assert plan_features.upload_window_active(user, created_at) is False


def test_download_window_negative_expired_path(monkeypatch):
    frozen_now = datetime(2026, 3, 26, 12, 0, 1, tzinfo=timezone.utc)
    _freeze_now(monkeypatch, frozen_now)

    user = SimpleNamespace(plan="ultimate")
    created_at = frozen_now - timedelta(days=360, seconds=1)

    assert plan_features.download_window_active(user, created_at) is False
