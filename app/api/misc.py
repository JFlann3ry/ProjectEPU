"""Misc public endpoints (home, faq, terms, health, sitemap)."""

# ruff: noqa: I001
import io
import re
from pathlib import Path
from urllib.parse import quote_plus
from xml.sax.saxutils import escape

import qrcode
from qrcode.constants import (
    ERROR_CORRECT_H,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
)
from qrcode.image.pil import PilImage
from PIL import Image
from PIL.Image import Resampling
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from sqlalchemy.orm import Session
from db import engine, get_db

from app.core.settings import settings
from app.core.templates import templates
from app.models.event import Event
from app.services.auth import get_current_user

router = APIRouter()
BASE_URL = settings.BASE_URL
# Last updated date for Terms (ISO format). Update when terms change.
TERMS_LAST_UPDATED = "2025-08-29"


@router.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    # Serve marketing homepage for everyone; show dashboard CTA if logged in
    return templates.TemplateResponse(request, "home.html", context={"user": user})


@router.get("/examples", response_class=HTMLResponse)
async def examples_page(request: Request):
    return templates.TemplateResponse(request, "examples.html")


@router.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return templates.TemplateResponse(
        request,
        "terms.html",
        context={"terms_last_updated": TERMS_LAST_UPDATED},
    )


@router.get("/terms/embed", response_class=HTMLResponse)
async def terms_embed(request: Request):
    """Return only the terms text content for embedding in modals/iframes."""
    return templates.TemplateResponse(
        request,
        "components/terms_text.html",
        context={"terms_last_updated": TERMS_LAST_UPDATED},
    )


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse(request, "privacy.html")


@router.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    """Frequently Asked Questions page with simple accordion UI."""
    # Group FAQs into themed sections. Keep answers concise; link to deeper docs.
    sections = [
        {
            "id": "getting-started",
            "title": "Getting started",
            "items": [
                {
                    "q": "How do I upload photos or videos?",
                    "a": (
                        "Open your event page and click Upload. Drag & drop files or "
                        "select them from your device. Progress is shown in real time. "
                        "New here? See the tutorial at /tutorial."
                    ),
                },
                {
                    "q": "Do guests need an account?",
                    "a": (
                        "Usually no. Guests can upload using the event link or code. "
                        "Hosts can optionally require a password in Event Settings."
                    ),
                },
                {
                    "q": "How do I share my event with guests?",
                    "a": (
                        "Use the Share button on your event to copy a link or generate "
                        "a QR code for invites and signage."
                    ),
                },
            ],
        },
        {
            "id": "uploads-media",
            "title": "Uploads and media",
            "items": [
                {
                    "q": "What file types are supported?",
                    "a": (
                        "Images: JPG, JPEG, PNG, HEIC. Videos: MP4, MOV. Raw formats "
                        "aren’t supported right now."
                    ),
                },
                {
                    "q": "Is there a file size or length limit?",
                    "a": (
                        "Images up to about 25 MB and short videos (a few minutes) work "
                        "well. Exact limits can vary by plan and network."
                    ),
                },
                {
                    "q": "Can I upload from mobile?",
                    "a": (
                        "Yes. The uploader works on modern mobile browsers. Large videos "
                        "may take longer depending on your connection."
                    ),
                },
                {
                    "q": "Can I delete or restore files?",
                    "a": (
                        "Event owners can soft-delete items from the gallery and restore "
                        "them from the Deleted view before they’re purged."
                    ),
                },
            ],
        },
        {
            "id": "gallery-features",
            "title": "Gallery and features",
            "items": [
                {
                    "q": "Who can see uploads to my event?",
                    "a": (
                        "Only people with your event’s share link/code (and password if "
                        "enabled). You can lock or unpublish anytime from Event Settings."
                    ),
                },
                {
                    "q": "Does the gallery support slideshows?",
                    "a": (
                        "Yes. Use the dedicated Live Slideshow at /live/{code} for a "
                        "full‑screen display that auto‑advances and picks up new uploads. "
                        "Keyboard: Space to pause/resume, ←/→ for previous/next, +/- to "
                        "change delay."
                    ),
                },
                {
                    "q": "Can I favorite or bulk select items?",
                    "a": (
                        "Yes. Use the selection toolbar for bulk actions like Delete, "
                        "ZIP, or Add to album. Favorites update immediately."
                    ),
                },
            ],
        },
        {
            "id": "plans-billing",
            "title": "Plans and billing",
            "items": [
                {
                    "q": "Do you offer refunds?",
                    "a": (
                        "If something went wrong with your purchase, contact support "
                        "with your order number. Eligibility depends on usage and time "
                        "since purchase."
                    ),
                },
                {
                    "q": "How long are files stored?",
                    "a": (
                        "Files remain available for the duration of your plan. If you "
                        "cancel or downgrade, we’ll notify you of any storage changes "
                        "in advance."
                    ),
                },
                {
                    "q": "Where can I view or change my plan?",
                    "a": (
                        "See the pricing page for plan details. Billing changes are "
                        "managed from your account’s billing section."
                    ),
                },
            ],
        },
        {
            "id": "privacy-security",
            "title": "Privacy and security",
            "items": [
                {
                    "q": "How is my data protected?",
                    "a": (
                        "We use industry-standard practices. Event POST actions include "
                        "CSRF protection. See /privacy for details."
                    ),
                },
                {
                    "q": "Can I request data deletion?",
                    "a": (
                        "Yes. Request account or data deletion from your Profile or by "
                        "contacting support."
                    ),
                },
                {
                    "q": "Do you track guests?",
                    "a": (
                        "We minimize personal data. Guests can upload without accounts; "
                        "hosts may require a password for extra privacy."
                    ),
                },
            ],
        },
        {
            "id": "troubleshooting",
            "title": "Troubleshooting",
            "items": [
                {
                    "q": "Uploads are slow or stuck",
                    "a": (
                        "Check your network and try fewer files at once. Very large "
                        "videos upload more slowly on mobile connections."
                    ),
                },
                {
                    "q": "A video won’t play in the gallery",
                    "a": (
                        "Make sure it’s MP4 or MOV. Some rare codecs may not play in all "
                        "browsers. Converting to H.264/AAC usually helps."
                    ),
                },
                {
                    "q": "I can’t find my event",
                    "a": (
                        "Confirm the share link or event code with the host, or ask them "
                        "to re-share the QR code."
                    ),
                },
            ],
        },
        # Note: removed the previous 'For developers' FAQ section per request.
    ]

    # Wrap sections to support both bracket and dot access without colliding with dict methods
    class _SectionAdapter:
        __slots__ = ("_data",)

        def __init__(self, data: dict):
            self._data = data

        def __getitem__(self, key):
            return self._data[key]

        def __getattr__(self, name):
            # Allow attribute-style access like sec.id, sec.title, and crucially sec.items
            if name in self._data:
                return self._data[name]
            raise AttributeError(name)

        def get(self, key, default=None):
            return self._data.get(key, default)

    sections_wrapped = [_SectionAdapter(sec) for sec in sections]

    # Provide a flat list for templates/tests that expect `qas`.
    qas_flat = [item for sec in sections for item in sec["items"]]
    return templates.TemplateResponse(
        request,
        "faq.html",
        context={"sections": sections_wrapped, "qas": qas_flat},
    )


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(request, "about.html")


@router.get("/tutorial", response_class=HTMLResponse)
async def tutorial_page(request: Request):
    steps = [
        {
            "id": "code",
            "title": "Find your event code",
            "desc": "Ask the host for the code or scan their QR.",
        },
        {
            "id": "login",
            "title": "Open guest login",
            "desc": "Enter the event code (and password if required).",
        },
        {
            "id": "terms",
            "title": "Agree to upload terms",
            "desc": "We’ll ask you to accept the terms before uploading.",
        },
        {
            "id": "select",
            "title": "Select or drag files",
            "desc": "Choose photos/videos or drag & drop them into the page.",
        },
        {
            "id": "upload",
            "title": "Upload & wait",
            "desc": "Watch progress; large videos may take longer.",
        },
        {
            "id": "view",
            "title": "View the shared gallery",
            "desc": "Enjoy everyone’s uploads together.",
        },
    ]
    return templates.TemplateResponse(request, "tutorial.html", context={"steps": steps})


@router.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    # Redirect to the canonical plans page, carrying any success/canceled message
    msg = None
    try:
        qp = dict(request.query_params)
        if qp.get("success"):
            msg = "Payment successful. You can now create events."
        elif qp.get("canceled"):
            msg = "Payment canceled. No changes were made."
    except Exception:
        msg = None
    target = "/pricing"
    if msg:
        target = f"{target}?message={quote_plus(msg)}"
    return RedirectResponse(target, status_code=303)


@router.get("/qr")
def generate_qr(
    path: str = Query(None),
    url: str = Query(None),
    # Theming
    theme: str = Query("classic", description="classic|dark|brand or custom via fg/bg"),
    fg: str | None = Query(None, description="Hex like #000000"),
    bg: str | None = Query(None, description="Hex like #ffffff"),
    # Sizing
    box_size: int = Query(10, ge=1, le=40),
    border: int = Query(4, ge=0, le=10),
    # Error correction
    ecc: str = Query("M", description="L|M|Q|H"),
    # Logo overlay
    logo: bool = Query(False),
    logo_size: int = Query(26, ge=5, le=40, description="Percent of QR size"),
    logo_url: str | None = Query(None, description="Absolute or /static/ logo URL (optional)"),
):
    # Resolve target URL
    if url:
        if url.startswith("http://") or url.startswith("https://"):
            full_url = url
        else:
            full_url = BASE_URL.rstrip("/") + "/" + url.lstrip("/")
    elif path:
        full_url = BASE_URL.rstrip("/") + "/" + path.lstrip("/")
    else:
        return Response(content="Missing path or url parameter", status_code=400)

    # Colors/theme
    hex_pat = re.compile(r"^#?[0-9a-fA-F]{6}$")
    def canon(x: str | None, fallback: str) -> str:
        if not x:
            return fallback
        if not hex_pat.match(x):
            return fallback
        return x if x.startswith("#") else ("#" + x)

    theme_l = (theme or "").lower()
    if fg or bg:
        fill_color = canon(fg, "#000000")
        back_color = canon(bg, "#ffffff")
    elif theme_l == "dark":
        # Dark card around, standard black-on-white QR for scan reliability
        fill_color = "#000000"
        back_color = "#ffffff"
    elif theme_l == "brand":
        # Use product blue for modules
        fill_color = "#4f8cff"
        back_color = "#ffffff"
    else:  # classic
        fill_color = "#000000"
        back_color = "#ffffff"

    # Error correction mapping
    ecc_map = {
        "L": ERROR_CORRECT_L,
        "M": ERROR_CORRECT_M,
        "Q": ERROR_CORRECT_Q,
        "H": ERROR_CORRECT_H,
    }
    ecc_val_in = (ecc or "M").upper()
    # If placing a logo and ECC not explicitly set higher, prefer H for robustness
    ecc_key = "H" if (logo and ecc_val_in == "M") else ecc_val_in
    ec_level = ecc_map.get(ecc_key, ERROR_CORRECT_M)

    # Build QR
    qr = qrcode.QRCode(
        version=None,
        error_correction=ec_level,
        box_size=box_size,
        border=border,
    )
    qr.add_data(full_url)
    qr.make(fit=True)
    img = qr.make_image(
        fill_color=fill_color,
        back_color=back_color,
        image_factory=PilImage,
    )
    pil = img.get_image()
    if pil.mode != "RGBA":
        pil = pil.convert("RGBA")

    # Optional logo overlay (center)
    if logo:
        try:
            mark = None
            if logo_url:
                # Support only local static assets for safety
                if logo_url.startswith("/static/"):
                    project_root = Path(__file__).resolve().parents[2]
                    fs_path = project_root / logo_url.lstrip("/")
                    if fs_path.exists():
                        mark = Image.open(fs_path).convert("RGBA")
            if mark is None:
                project_root = Path(__file__).resolve().parents[2]
                logo_path = project_root / "static" / "favicon.png"
                if logo_path.exists():
                    mark = Image.open(logo_path).convert("RGBA")
            if mark is not None:
                # Fit logo into desired percentage of QR
                max_side = int(min(img.size) * (logo_size / 100.0))
                if max_side > 0:
                    mark.thumbnail((max_side, max_side), Resampling.LANCZOS)
                    # Center paste
                    px = (pil.width - mark.width) // 2
                    py = (pil.height - mark.height) // 2
                    pil.alpha_composite(mark, dest=(px, py))
        except Exception:
            # Fail open: still return QR without logo
            pass

    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    buf.seek(0)
    headers = {"Cache-Control": "public, max-age=3600"}
    return StreamingResponse(buf, media_type="image/png", headers=headers)


@router.get("/health")
def health_check():
    # Check required settings presence (don’t leak values)
    missing = []
    if not settings.DB_SERVER:
        missing.append("DB_SERVER")
    if not settings.DB_USER:
        missing.append("DB_USER")
    if not settings.DB_PASSWORD:
        missing.append("DB_PASSWORD")
    if settings.SECRET_KEY == "CHANGE_THIS_TO_A_SECRET_KEY" or not settings.SECRET_KEY:
        missing.append("SECRET_KEY")

    # Check DB connectivity best-effort
    db_ok = False
    db_error = None
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        db_ok = True
    except Exception as e:
        db_error = str(e)

    status = "ok" if db_ok and not missing else ("degraded" if db_ok else "error")
    from datetime import datetime, timezone
    payload = {
        "status": status,
        "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config": {
            "base_url_set": bool(settings.BASE_URL),
            "db": {
                "driver": settings.DB_DRIVER,
                "server_set": bool(settings.DB_SERVER),
                "user_set": bool(settings.DB_USER),
                "name_set": bool(settings.DB_NAME),
            },
            "email_configured": bool(settings.GMAIL_USER and settings.GMAIL_PASS),
            "stripe_pub_set": bool(settings.STRIPE_PUBLISHABLE_KEY),
            "stripe_sec_set": bool(settings.STRIPE_SECRET_KEY),
        },
        "missing": missing,
        "db": {"ok": db_ok, "error": db_error},
    }
    # Always return 200 per acceptance; status is in payload
    return JSONResponse(content=payload, status_code=200)


@router.get("/health.txt")
def health_text():
    # simple OK text for load balancer checks
    return Response(content="OK", media_type="text/plain")


@router.get("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /profile",
        "Disallow: /profile/edit",
        f"Sitemap: {BASE_URL.rstrip('/')}/sitemap.xml",
        "",
    ]
    return Response(content="\n".join(lines), media_type="text/plain")


@router.get("/sitemap.xml")
def sitemap_xml(db: Session = Depends(get_db)):

    base = BASE_URL.rstrip("/")
    urls = [
        f"{base}/",
    f"{base}/pricing",
        f"{base}/terms",
        f"{base}/privacy",
        f"{base}/faq",
        f"{base}/about",
        f"{base}/tutorial",
        f"{base}/gallery",
    ]
    # Public share pages for published events (simple assumption)
    events = db.query(Event).filter(Event.Published).limit(5000).all()
    for ev in events:
        code = getattr(ev, "Code", None)
        if code:
            urls.append(f"{base}/e/{code}")
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        parts.append("  <url>")
        parts.append(f"    <loc>{escape(u)}</loc>")
        parts.append("  </url>")
    parts.append("</urlset>")
    xml = "\n".join(parts)
    return Response(content=xml, media_type="application/xml")
