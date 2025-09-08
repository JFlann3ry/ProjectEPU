"""MIME detection helpers.

Uses `magic` if available (provided by python-magic or python-magic-bin),
falls back to provided content type or application/octet-stream.
"""

from __future__ import annotations

from typing import Optional, Tuple


def sniff_mime(data: bytes, fallback_content_type: Optional[str] = None) -> str:
    try:
        import magic  # type: ignore

        try:
            m = magic.Magic(mime=True)
            detected = m.from_buffer(data)
        except Exception:
            # Some variants expose from_buffer at module level
            detected = magic.from_buffer(data, mime=True)  # type: ignore
        if isinstance(detected, str) and detected:
            return detected
    except Exception:
        pass
    return fallback_content_type or "application/octet-stream"


def is_allowed_mime(
    data: bytes,
    allowed_prefixes: Tuple[str, ...] = ("image/", "video/"),
    fallback_content_type: Optional[str] = None,
) -> tuple[bool, str]:
    """Return (allowed, mime) using sniffed MIME with fallback."""
    mime = sniff_mime(data, fallback_content_type)
    if not allowed_prefixes:
        return True, mime
    ok = any(mime.startswith(p) for p in allowed_prefixes)
    return ok, mime
