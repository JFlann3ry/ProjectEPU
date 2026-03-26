from types import SimpleNamespace

from app.core.security_preflight import run_security_preflight


def _unsafe_cfg() -> SimpleNamespace:
    return SimpleNamespace(
        DB_SERVER="",
        DB_USER="",
        DB_PASSWORD="",
        SECRET_KEY="CHANGE_THIS_TO_A_SECRET_KEY",
        DEBUG_ROUTES_ENABLED=True,
        BASE_URL="http://example.com",
        COOKIE_SECURE=False,
    )


def test_security_preflight_fails_in_production_mode_for_unsafe_config():
    code, production_mode, problems = run_security_preflight(
        _unsafe_cfg(),
        mode="production",
        strict=False,
        env="",
        app_env="",
    )
    assert production_mode is True
    assert code == 1
    assert problems


def test_security_preflight_warns_but_does_not_fail_in_development_without_strict():
    code, production_mode, problems = run_security_preflight(
        _unsafe_cfg(),
        mode="development",
        strict=False,
        env="",
        app_env="",
    )
    assert production_mode is False
    assert code == 0
    assert problems


def test_security_preflight_fails_in_development_when_strict_enabled():
    code, production_mode, problems = run_security_preflight(
        _unsafe_cfg(),
        mode="development",
        strict=True,
        env="",
        app_env="",
    )
    assert production_mode is False
    assert code == 1
    assert problems
