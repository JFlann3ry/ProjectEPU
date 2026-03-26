from types import SimpleNamespace

from app.core.settings import validate_production_settings


def test_validate_production_settings_flags_unsafe_defaults():
    cfg = SimpleNamespace(
        DB_SERVER="",
        DB_USER="",
        DB_PASSWORD="",
        SECRET_KEY="CHANGE_THIS_TO_A_SECRET_KEY",
        DEBUG_ROUTES_ENABLED=True,
        BASE_URL="http://example.com",
        COOKIE_SECURE=False,
    )

    problems = validate_production_settings(cfg)

    assert any("DB_SERVER" in p for p in problems)
    assert any("DB_USER" in p for p in problems)
    assert any("DB_PASSWORD" in p for p in problems)
    assert any("SECRET_KEY" in p for p in problems)
    assert any("DEBUG_ROUTES_ENABLED" in p for p in problems)
    assert any("BASE_URL" in p for p in problems)
    assert any("COOKIE_SECURE" in p for p in problems)


def test_validate_production_settings_accepts_hardened_config():
    cfg = SimpleNamespace(
        DB_SERVER="sql.example.internal",
        DB_USER="epu_user",
        DB_PASSWORD="super_secret",
        SECRET_KEY="a-really-long-random-secret",
        DEBUG_ROUTES_ENABLED=False,
        BASE_URL="https://epu.example.com",
        COOKIE_SECURE=True,
    )

    problems = validate_production_settings(cfg)

    assert problems == []
