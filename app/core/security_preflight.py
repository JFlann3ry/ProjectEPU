from __future__ import annotations

from app.core.settings import validate_production_settings


def resolve_production_mode(mode: str, *, env: str = "", app_env: str = "") -> bool:
    normalized = str(mode or "auto").strip().lower()
    if normalized == "production":
        return True
    if normalized == "development":
        return False
    env_norm = str(env or "").strip().lower()
    app_env_norm = str(app_env or "").strip().lower()
    return env_norm in {"prod", "production"} or app_env_norm in {"prod", "production"}


def evaluate_critical_settings(cfg) -> list[str]:
    return list(validate_production_settings(cfg))


def run_security_preflight(
    cfg,
    *,
    mode: str = "auto",
    strict: bool = False,
    env: str = "",
    app_env: str = "",
) -> tuple[int, bool, list[str]]:
    production_mode = resolve_production_mode(mode, env=env, app_env=app_env)
    problems = evaluate_critical_settings(cfg)
    should_fail = bool(production_mode or strict)
    exit_code = 1 if (should_fail and problems) else 0
    return exit_code, production_mode, problems


def format_report(*, production_mode: bool, strict: bool, problems: list[str]) -> str:
    lines: list[str] = []
    lines.append(f"mode={'production' if production_mode else 'development'}")
    lines.append(f"strict={'true' if strict else 'false'}")
    if problems:
        lines.append("status=failed")
        lines.append("problems:")
        lines.extend([f"- {p}" for p in problems])
    else:
        lines.append("status=ok")
        lines.append("problems: []")
    return "\n".join(lines)
