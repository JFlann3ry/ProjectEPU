from typing import Tuple

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database (set via .env; avoid hardcoding secrets here)
    DB_SERVER: str = ""  # e.g. 192.168.1.50 or hostname
    DB_NAME: str = "EPU"
    DB_USER: str = ""  # e.g. EPUWebUser
    DB_PASSWORD: str = ""  # strong password
    DB_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_PORT: int = 1433

    # Security
    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECRET_KEY"

    # App/Base URL
    BASE_URL: str = "http://localhost:4200"

    # Email
    GMAIL_USER: str = ""
    GMAIL_PASS: str = ""
    GMAIL_APP_PASSWORD: str = ""
    SUPPORT_EMAIL_TO: str = ""  # destination inbox for support/contact

    # Stripe
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_JSON: bool = True
    LOG_FILE: str = "logs/app.log"
    LOG_MAX_BYTES: int = 5_000_000  # 5 MB
    LOG_BACKUP_COUNT: int = 5

    # Sentry
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0

    # Upload/security
    MAX_UPLOAD_BYTES: int = 200_000_000  # 200 MB per file default
    ALLOWED_UPLOAD_MIME_PREFIXES: Tuple[str, ...] = ("image/", "video/")
    COOKIE_SECURE: bool = False  # override to True in prod; or auto-detected from BASE_URL
    # Auth rate-limiting
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 15 * 60  # 15 minutes
    # Contact rate limiting and simple CAPTCHA
    CONTACT_RATE_LIMIT_WINDOW_SECONDS: int = 60  # 1 minute window
    CONTACT_RATE_LIMIT_ATTEMPTS: int = 3
    CAPTCHA_SECRET: str = ""  # if using hCaptcha/Cloudflare Turnstile; leave empty to disable
    CAPTCHA_PROVIDER: str = "turnstile"  # or 'hcaptcha'

    # Redis (for shared rate limiting)
    REDIS_URL: str = ""

    # AWS S3 Storage (optional; local filesystem if not configured)
    AWS_REGION: str = ""
    AWS_ACCESS_KEY_ID: str = ""  # Optional; uses IAM role on EC2
    AWS_SECRET_ACCESS_KEY: str = ""  # Optional; uses IAM role on EC2
    S3_UPLOADS_BUCKET: str = ""  # If empty, uses local filesystem

    # Debug/dev-only routes flag
    # Enable in development; should be disabled in production deployments.
    DEBUG_ROUTES_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

# Basic validation for required settings to prevent confusing runtime errors
_missing = []
if not settings.DB_SERVER:
    _missing.append("DB_SERVER")
if not settings.DB_USER:
    _missing.append("DB_USER")
if not settings.DB_PASSWORD:
    _missing.append("DB_PASSWORD")
if settings.SECRET_KEY == "CHANGE_THIS_TO_A_SECRET_KEY" or not settings.SECRET_KEY:
    _missing.append("SECRET_KEY")

if _missing:
    # Do not crash imports in some tools; instead, provide a helpful message.
    import warnings

    warnings.warn(
        "Missing required settings in .env: "
        + ", ".join(_missing)
        + ". Update e:/ProjectEPU/.env and restart the app."
    )

# Auto-detect secure cookies when running under HTTPS
try:
    if not getattr(settings, "COOKIE_SECURE", False) and str(
        getattr(settings, "BASE_URL", "")
    ).lower().startswith("https"):
        # Flip to True if BASE_URL suggests HTTPS
        settings.COOKIE_SECURE = True  # type: ignore[attr-defined]
except Exception:
    # Best-effort only; ignore if settings are missing
    pass
