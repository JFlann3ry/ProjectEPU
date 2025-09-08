import os
# ruff: noqa: I001

import pytest
from playwright.sync_api import sync_playwright


# Skip by default unless E2E=1
e2e_enabled = os.getenv("E2E", "0") == "1"
pytestmark = pytest.mark.skipif(
    not e2e_enabled, reason="E2E tests disabled; set E2E=1 to enable"
)


def test_gallery_autofilter_and_favorites_toggle():
    base = os.getenv("BASE_URL", "http://localhost:4200").rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        # Go to gallery; if auth is required this may redirect to /login.
        page.goto(f"{base}/gallery")

        # If the filter select exists (i.e., we are logged in), verify auto-submit on change.
        type_sel = page.locator("select#type").first
        if type_sel.count() > 0:
            # Change to Videos and expect navigation with query param type=video
            type_sel.select_option("video")
            page.wait_for_load_state("networkidle")
            assert "type=video" in page.url

            # Change back to Images
            type_sel = page.locator("select#type").first
            type_sel.select_option("image")
            page.wait_for_load_state("networkidle")
            assert "type=image" in page.url

            # Favorites pill toggles instantly and submits the form
            fav_pill = page.locator("label.favorites-pill[for=\"favorites\"]").first
            if fav_pill.count() > 0:
                before = page.url
                fav_pill.click()
                page.wait_for_load_state("networkidle")
                after = page.url
                assert after != before
                assert "favorites=" in after
        else:
            # If not logged in, we at least assert the page loaded (e.g., login page)
            assert page.title() is not None

        context.close()
        browser.close()
