"""Utilities for resolving and normalizing event theme values.

This module centralizes theme fallback rules so edit and guest pages render
from the same effective values.
"""

from __future__ import annotations

from typing import Any


def _s(value: Any) -> str | None:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None


def normalize_button_style(value: Any, default: str = "gradient") -> str:
    text = (_s(value) or "").lower()
    return text if text in ("gradient", "solid") else default


def normalize_gradient_style(value: Any, default: str = "linear") -> str:
    text = (_s(value) or "").lower()
    return text if text in ("linear", "radial") else default


def normalize_gradient_direction(value: Any, default: str = "90deg") -> str:
    text = (_s(value) or "").lower()
    return text if text.endswith("deg") else default


def resolve_effective_theme(custom: Any = None, theme: Any = None) -> dict[str, Any]:
    """Return a single source of truth for effective theme values.

    Precedence: event customization first, then selected theme, then defaults.
    """

    def pick(custom_attr: str, theme_attr: str, default: Any = None) -> Any:
        cval = getattr(custom, custom_attr, None) if custom is not None else None
        if cval not in (None, ""):
            return cval
        tval = getattr(theme, theme_attr, None) if theme is not None else None
        if tval not in (None, ""):
            return tval
        return default

    return {
        "bg": pick("BackgroundColour", "BackgroundColour", "#ffffff"),
        "text": pick("TextColour", "TextColour", "#0F0E17"),
        "btn1": pick("ButtonColour1", "ButtonColour1", "#F25F4C"),
        "btn2": pick("ButtonColour2", "ButtonColour2", "#FF8906"),
        "accent": pick("AccentColour", "AccentColour", "#222"),
        "font": pick("FontFamily", "FontFamily", "Inter, Arial, sans-serif"),
        "input_bg": pick("InputBackgroundColour", "InputBackgroundColour", "#15161e"),
        "dropzone_bg": pick("DropzoneBackgroundColour", "DropzoneBackgroundColour", "#121424"),
        "bg_img": pick("CoverPhotoPath", "CoverPhotoPath", None),
        "button_style": normalize_button_style(pick("ButtonStyle", "ButtonStyle", "gradient")),
        "button_gradient_style": normalize_gradient_style(
            pick("ButtonGradientStyle", "ButtonGradientStyle", "linear")
        ),
        "button_gradient_direction": normalize_gradient_direction(
            pick("ButtonGradientDirection", "ButtonGradientDirection", "90deg")
        ),
        "heading_size": (_s(getattr(custom, "HeadingSize", None)) or "m").lower(),
        "corner_radius": (_s(getattr(custom, "CornerRadius", None)) or "rounded").lower(),
    }


def build_theme_view(effective_theme: Any = None, page_bg: str = "#0b0b10") -> dict[str, Any]:
    """Build a template-friendly view model from effective theme values."""

    src = effective_theme or {}

    def getv(key: str, default: Any = None) -> Any:
        if isinstance(src, dict):
            val = src.get(key, default)
        else:
            val = getattr(src, key, default)
        return default if val in (None, "") else val

    gsty = normalize_gradient_style(getv("button_gradient_style", "linear"))
    gdir = normalize_gradient_direction(getv("button_gradient_direction", "90deg"))

    return {
        "tv": {
            "bg": getv("bg", "#ffffff"),
            "text": getv("text", "#0F0E17"),
            "page_bg": page_bg,
            "btn1": getv("btn1", "#F25F4C"),
            "btn2": getv("btn2", "#FF8906"),
            "accent": getv("accent", "#222"),
            "font": getv("font", "Inter, Arial, sans-serif"),
            "input_bg": getv("input_bg", "#15161e"),
            "dropzone_bg": getv("dropzone_bg", "#121424"),
            "bg_img": getv("bg_img", None),
            "gsty": gsty,
            "gdir": gdir,
        },
        "hs": getv("heading_size", "m"),
        "cr": getv("corner_radius", "rounded"),
        "bs": normalize_button_style(getv("button_style", "gradient")),
        "gsty": gsty,
        "gdir": gdir,
    }
