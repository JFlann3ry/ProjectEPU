import logging
import time
import traceback
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi import HTTPException as FastAPIHTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import PlainTextResponse, RedirectResponse

from app.api import (
    account,
    admin,
    auth,
    billing,
    live,
    events,
    events_create,
    extras,
    gallery,
    guest,
    logout,
    misc,
    photo_order,
    profile,
    profile_edit,
    support,
    uploads,
)
from app.core.logging_utils import configure_logging
from app.core.middleware_compression import add_compression_middleware
from app.core.settings import settings
from app.core.templates import templates
from app.models import AppErrorLog
from app.services.auth import get_user_id_from_request
from app.services.s3_storage import S3StorageService
from db import get_db

try:
    import sentry_sdk  # type: ignore
    from sentry_sdk.integrations.starlette import StarletteIntegration  # type: ignore
except Exception:
    sentry_sdk = None  # type: ignore

load_dotenv()


app = FastAPI()
add_compression_middleware(app)

# Configure logging (console + rotating file; JSON by default)
configure_logging(settings)
logger = logging.getLogger("app")

# Initialize S3 storage service (optional; uses local filesystem fallback)
s3_service = None
if getattr(settings, "S3_UPLOADS_BUCKET", ""):
    try:
        s3_service = S3StorageService(
            region=settings.AWS_REGION,
            bucket=settings.S3_UPLOADS_BUCKET,
            access_key=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            secret_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        )
        logger.info("S3 storage service initialized")
    except Exception as e:
        logger.warning(f"S3 initialization failed; falling back to local filesystem: {e}")
        s3_service = None
else:
    logger.info("S3_UPLOADS_BUCKET not configured; using local filesystem")

# Initialize Sentry if DSN provided
if getattr(settings, "SENTRY_DSN", "") and sentry_sdk is not None:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[StarletteIntegration()],
        traces_sample_rate=float(getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.0) or 0.0),
        send_default_pii=False,
    )

# Store S3 service in app state for dependency injection in routes
app.state.s3_service = s3_service

# Mount static folders
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

app.include_router(uploads.router)
# Register static path routes before parameterized /events/{event_id} to avoid 422 on /events/create
app.include_router(events_create.router)
app.include_router(events.router)
app.include_router(profile.router)
app.include_router(profile_edit.router)
app.include_router(auth.router)
app.include_router(guest.router)
app.include_router(account.router)
app.include_router(live.router)
app.include_router(gallery.router)
app.include_router(photo_order.router)
app.include_router(misc.router)
app.include_router(logout.router)
app.include_router(billing.router)
app.include_router(admin.router)
app.include_router(support.router)
app.include_router(extras.router)


# Serve favicon
@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/favicon.png")




# Request logging middleware with request id and user/session context
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.perf_counter()
    # Ensure duration_ms is always defined to avoid UnboundLocalError in exception paths
    duration_ms: Optional[int] = None
    # Stash request_id for downstream handlers
    request.state.request_id = request_id
    user_id: Optional[int] = None
    try:
        # Best-effort extract user id without forcing DB if dependency available
        if request.cookies.get("session_id"):
            from db import get_db  # local import to avoid circulars

            db_gen = get_db()
            db = next(db_gen)
            try:
                user_id = get_user_id_from_request(request, db)
            finally:
                try:
                    next(db_gen)
                except StopIteration:
                    pass
    except Exception:
        pass

    extra_ctx = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else None,
        "user_id": user_id,
        "referer": request.headers.get("referer"),
        "user_agent": request.headers.get("user-agent"),
    }
    logger.info("request.start", extra=extra_ctx)
    try:
        response = await call_next(request)
    except Exception:
        # Compute duration on error, then log and re-raise for global handler
        if duration_ms is None:
            duration_ms = int((time.perf_counter() - start) * 1000)
        logger.exception("request.error", extra={**extra_ctx, "duration_ms": duration_ms})
        # Re-raise to be handled by 500 handler
        raise

    duration_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request.end",
        extra={**extra_ctx, "status_code": response.status_code, "duration_ms": duration_ms},
    )
    return response


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    # Render custom 404 page if available
    try:
        # Best-effort DB log for 404 with request context
        try:
            request_id = getattr(request.state, "request_id", None)
            db_gen = get_db()
            db = next(db_gen)
            err = AppErrorLog(
                RequestID=str(request_id) if request_id else None,
                Path=str(request.url.path),
                Method=request.method,
                StatusCode=404,
                UserID=None,
                ClientIP=request.client.host if request.client else None,
                UserAgent=request.headers.get("user-agent"),
                Referer=request.headers.get("referer"),
                Message="Not Found",
                StackTrace=None,
            )
            db.add(err)
            db.commit()
        except Exception:
            pass
        resp = templates.TemplateResponse(request, "404.html", status_code=404)
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            resp.headers["X-Request-ID"] = str(request_id)
        return resp
    except Exception:
        return PlainTextResponse("Not Found", status_code=404)


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    """Log all HTTPException (>=400) to DB, then return a JSON response.

    Note: 404 has a dedicated handler above which also logs to DB.
    """
    status = getattr(exc, "status_code", 500) or 500
    try:
        if status >= 400 and status != 404:
            request_id = getattr(request.state, "request_id", None)
            db_gen = get_db()
            db = next(db_gen)
            user_id = None
            try:
                user_id = get_user_id_from_request(request, db)
            except Exception:
                pass
            err = AppErrorLog(
                RequestID=str(request_id) if request_id else None,
                Path=str(request.url.path),
                Method=request.method,
                StatusCode=int(status),
                UserID=user_id,
                ClientIP=request.client.host if request.client else None,
                UserAgent=request.headers.get("user-agent"),
                Referer=request.headers.get("referer"),
                Message=str(getattr(exc, "detail", "HTTP error")),
                StackTrace=None,
            )
            db.add(err)
            db.commit()
    except Exception:
        pass
    # If this is a redirect (302/303/etc) and a Location header is present,
    # return a RedirectResponse so browsers perform a proper HTML redirect
    if status in (301, 302, 303, 307, 308):
        loc = None
        try:
            # FastAPI stores headers on the exception; guard attribute access
            if hasattr(exc, "headers") and exc.headers:
                loc = exc.headers.get("Location")
            else:
                loc = None
        except Exception:
            loc = None
        if loc:
            return RedirectResponse(url=loc, status_code=status)

    # Mirror FastAPI default JSON structure for non-redirects
    request_id = getattr(request.state, "request_id", None)
    resp = JSONResponse({"detail": exc.detail}, status_code=status)
    if request_id:
        resp.headers["X-Request-ID"] = str(request_id)
    return resp


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    try:
        # Attach request id if available
        request_id = getattr(request.state, "request_id", None)
        # Best-effort write error to DB with request_id
        try:
            db_gen = get_db()
            db = next(db_gen)
            user_id = None
            try:
                user_id = get_user_id_from_request(request, db)
            except Exception:
                pass
            err = AppErrorLog(
                RequestID=str(request_id) if request_id else None,
                Path=str(request.url.path),
                Method=request.method,
                StatusCode=500,
                UserID=user_id,
                ClientIP=request.client.host if request.client else None,
                UserAgent=request.headers.get("user-agent"),
                Referer=request.headers.get("referer"),
                Message=str(exc),
                StackTrace="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            )
            db.add(err)
            db.commit()
        except Exception:
            # Swallow DB logging errors to not mask original error
            pass
        resp = templates.TemplateResponse(
            request,
            "500.html",
            context={"request_id": request_id},
            status_code=500,
        )
        if request_id:
            resp.headers["X-Request-ID"] = str(request_id)
        return resp
    except Exception:
        return PlainTextResponse("Internal Server Error", status_code=500)
