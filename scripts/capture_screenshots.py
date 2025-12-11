import argparse
import os
from pathlib import Path
from typing import Iterable, List, Tuple

from playwright.sync_api import sync_playwright

DEFAULT_PAGES: List[Tuple[str, str]] = [
    ("home", "/"),
    ("pricing", "/pricing"),
    ("extras", "/extras"),
    ("extras-live-gallery", "/extras/live_gallery"),
    ("extras-qr-cards", "/extras/qr_cards"),
    ("examples", "/examples"),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Capture website screenshots for docs/tutorials",
    )
    p.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", "http://localhost:4200"),
        help="Base URL of the running app",
    )
    p.add_argument(
        "--out",
        default=str(Path("static/images/tutorial").as_posix()),
        help="Output directory for screenshots",
    )
    p.add_argument(
        "--pages",
        default=None,
        help="Comma-separated list of label:path (e.g., home:/,pricing:/pricing)",
    )
    p.add_argument("--fullpage", action="store_true", help="Capture full page height")
    p.add_argument("--no-mobile", action="store_true", help="Skip mobile viewport captures")
    p.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay in seconds after load before capture",
    )
    return p.parse_args()


def parse_pages(raw: str | None) -> List[Tuple[str, str]]:
    if not raw:
        return DEFAULT_PAGES
    out: List[Tuple[str, str]] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            # assume path; label from slug
            path = chunk
            label = chunk.strip("/").replace("/", "-") or "home"
        else:
            label, path = chunk.split(":", 1)
            label = label.strip()
            path = path.strip()
        out.append((label, path))
    return out


def ensure_dir(d: str | Path) -> Path:
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


def capture(
    base_url: str,
    out_dir: Path,
    pages: Iterable[Tuple[str, str]],
    fullpage: bool,
    do_mobile: bool,
    delay: float,
) -> None:
    with sync_playwright() as pw:
        # Desktop context
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # Mobile context (iPhone 12-ish)
        mctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"
                " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0"
                " Mobile/15E148 Safari/604.1"
            ),
        )
        mpage = mctx.new_page()

        for label, path in pages:
            url = base_url.rstrip("/") + path
            # Desktop
            page.goto(url, wait_until="networkidle")
            if delay:
                page.wait_for_timeout(int(delay * 1000))
            page.screenshot(
                path=str(out_dir / f"{label}-desktop.png"),
                full_page=fullpage,
            )
            # Mobile
            if do_mobile:
                mpage.goto(url, wait_until="networkidle")
                if delay:
                    mpage.wait_for_timeout(int(delay * 1000))
                mpage.screenshot(
                    path=str(out_dir / f"{label}-mobile.png"),
                    full_page=fullpage,
                )

        ctx.close()
        mctx.close()
        browser.close()


def main() -> None:
    args = parse_args()
    out_dir = ensure_dir(args.out)
    pages = parse_pages(args.pages)
    capture(args.base_url, out_dir, pages, args.fullpage, not args.no_mobile, args.delay)
    print(f"Saved screenshots to {out_dir}")


if __name__ == "__main__":
    main()
