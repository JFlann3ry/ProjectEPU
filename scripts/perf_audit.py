"""Simple page performance budget audit.

This script fetches key pages, inspects HTML payload size and first-byte time,
then follows same-origin CSS/JS assets to compute aggregate transfer budgets.

Usage:
  python scripts/perf_audit.py --base-url http://localhost:4200
  python scripts/perf_audit.py --base-url http://localhost:4200 --soft-fail
  python scripts/perf_audit.py --budgets scripts/perf_budgets.json
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

DEFAULT_PATHS = ["/", "/pricing", "/about", "/tutorial", "/contact"]
DEFAULT_BUDGETS: dict[str, int] = {
    "max_ttfb_ms": 1500,
    "max_html_bytes": 220_000,
    "max_css_bytes": 380_000,
    "max_js_bytes": 520_000,
    "max_total_asset_bytes": 1_000_000,
    "max_assets": 55,
}


@dataclass
class FetchResult:
    url: str
    status: int
    bytes: int
    duration_ms: int
    body: str


def _fetch_text(url: str, timeout: float) -> FetchResult:
    req = Request(url, headers={"User-Agent": "EPUPerfAudit/1.0"})
    started = time.perf_counter()
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        status = int(getattr(resp, "status", 200))
    duration_ms = int((time.perf_counter() - started) * 1000)
    text = raw.decode("utf-8", errors="replace")
    return FetchResult(
        url=url,
        status=status,
        bytes=len(raw),
        duration_ms=duration_ms,
        body=text,
    )


def _fetch_bytes(url: str, timeout: float) -> tuple[int, int, int]:
    req = Request(url, headers={"User-Agent": "EPUPerfAudit/1.0"})
    started = time.perf_counter()
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        status = int(getattr(resp, "status", 200))
    duration_ms = int((time.perf_counter() - started) * 1000)
    return status, len(raw), duration_ms


def _extract_assets(html: str, page_url: str, base_origin: str) -> tuple[set[str], set[str]]:
    css_urls: set[str] = set()
    js_urls: set[str] = set()

    for href in re.findall(r"<link[^>]+href=[\"']([^\"']+)[\"'][^>]*>", html, flags=re.I):
        candidate = urljoin(page_url, href)
        parsed = urlparse(candidate)
        if parsed.scheme not in ("http", "https"):
            continue
        if f"{parsed.scheme}://{parsed.netloc}" != base_origin:
            continue
        if ".css" in parsed.path:
            css_urls.add(candidate)

    for src in re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"'][^>]*>", html, flags=re.I):
        candidate = urljoin(page_url, src)
        parsed = urlparse(candidate)
        if parsed.scheme not in ("http", "https"):
            continue
        if f"{parsed.scheme}://{parsed.netloc}" != base_origin:
            continue
        js_urls.add(candidate)

    return css_urls, js_urls


def _load_budgets(path: str | None) -> dict[str, int]:
    budgets = dict(DEFAULT_BUDGETS)
    if not path:
        return budgets
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Budget file must be a JSON object")
    for key, value in raw.items():
        if key in budgets:
            budgets[key] = int(value)
    return budgets


def audit(
    base_url: str,
    paths: list[str],
    budgets: dict[str, int],
    timeout: float,
) -> dict[str, Any]:
    root = base_url.rstrip("/")
    parsed_root = urlparse(root)
    base_origin = f"{parsed_root.scheme}://{parsed_root.netloc}"

    pages: list[dict[str, Any]] = []
    violations: list[str] = []

    for path in paths:
        url = f"{root}{path if path.startswith('/') else '/' + path}"
        try:
            page = _fetch_text(url, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            msg = f"{path}: fetch failed ({type(exc).__name__})"
            pages.append({"path": path, "url": url, "error": msg})
            violations.append(msg)
            continue

        css_urls, js_urls = _extract_assets(page.body, page.url, base_origin)

        css_bytes = 0
        js_bytes = 0
        asset_count = 0

        for asset_url in sorted(css_urls):
            try:
                status, size, _duration = _fetch_bytes(asset_url, timeout=timeout)
                if status < 400:
                    css_bytes += size
                    asset_count += 1
            except Exception:
                violations.append(f"{path}: failed to fetch CSS asset {asset_url}")

        for asset_url in sorted(js_urls):
            try:
                status, size, _duration = _fetch_bytes(asset_url, timeout=timeout)
                if status < 400:
                    js_bytes += size
                    asset_count += 1
            except Exception:
                violations.append(f"{path}: failed to fetch JS asset {asset_url}")

        total_asset_bytes = css_bytes + js_bytes

        page_row = {
            "path": path,
            "url": url,
            "status": page.status,
            "ttfb_ms": page.duration_ms,
            "html_bytes": page.bytes,
            "css_bytes": css_bytes,
            "js_bytes": js_bytes,
            "total_asset_bytes": total_asset_bytes,
            "asset_count": asset_count,
        }
        pages.append(page_row)

        if page.status >= 400:
            violations.append(f"{path}: status {page.status}")
        if page.duration_ms > budgets["max_ttfb_ms"]:
            violations.append(f"{path}: ttfb {page.duration_ms}ms > {budgets['max_ttfb_ms']}ms")
        if page.bytes > budgets["max_html_bytes"]:
            violations.append(f"{path}: html {page.bytes}B > {budgets['max_html_bytes']}B")
        if css_bytes > budgets["max_css_bytes"]:
            violations.append(f"{path}: css {css_bytes}B > {budgets['max_css_bytes']}B")
        if js_bytes > budgets["max_js_bytes"]:
            violations.append(f"{path}: js {js_bytes}B > {budgets['max_js_bytes']}B")
        if total_asset_bytes > budgets["max_total_asset_bytes"]:
            violations.append(
                f"{path}: assets {total_asset_bytes}B > {budgets['max_total_asset_bytes']}B"
            )
        if asset_count > budgets["max_assets"]:
            violations.append(f"{path}: assets count {asset_count} > {budgets['max_assets']}")

    return {
        "base_url": root,
        "budgets": budgets,
        "pages": pages,
        "violations": violations,
        "ok": len(violations) == 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run page performance budget audit")
    parser.add_argument("--base-url", default="http://localhost:4200")
    parser.add_argument("--path", action="append", dest="paths")
    parser.add_argument("--budgets", default="")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output", default="")
    parser.add_argument(
        "--soft-fail",
        action="store_true",
        help="Exit 0 even when budget violations are found",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = args.paths if args.paths else list(DEFAULT_PATHS)
    budgets = _load_budgets(args.budgets or None)

    report = audit(
        base_url=args.base_url,
        paths=paths,
        budgets=budgets,
        timeout=float(args.timeout),
    )

    rendered = json.dumps(report, indent=2)
    print(rendered)

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")

    if report["ok"] or args.soft_fail:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
