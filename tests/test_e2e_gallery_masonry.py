import os
import pytest

from playwright.sync_api import sync_playwright


# Skip by default unless E2E=1
e2e_enabled = os.getenv("E2E", "0") == "1"
pytestmark = pytest.mark.skipif(not e2e_enabled, reason="E2E tests disabled; set E2E=1 to enable")


def test_gallery_masonry_columns_and_ordinals():
    base = os.getenv("BASE_URL", "http://localhost:4200").rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        page.goto(f"{base}/gallery")
        page.wait_for_load_state("networkidle")

        # Wait a moment for JS to render columns
        page.wait_for_timeout(600)

        # If page redirected to login, test is not applicable
        if page.url.endswith("/login"):
            pytest.skip("Not authenticated; skipping masonry layout E2E")

        # Detect our masonry wrapper
        wrapper = page.locator("#gallery > .masonry-columns").first
        if wrapper.count() == 0:
            # If no wrapper present, fall back to checking grid columns (CSS grid)
            # Count visible columns by sampling gallery width and item widths
            gal = page.locator("#gallery").first
            w = gal.bounding_box()
            items = page.locator("#gallery > .gallery-item")
            if items.count() == 0:
                pytest.skip("No gallery items rendered")
            item_w = items.nth(0).bounding_box()
            if not w or not item_w:
                pytest.skip("Unable to determine dimensions")
            approx_cols = max(1, int(round(w['width'] / item_w['width'])))
            assert 1 <= approx_cols <= 6
        else:
            cols = wrapper.locator('.masonry-column')
            cnt = cols.count()
            assert cnt >= 2 and cnt <= 6, f"unexpected column count: {cnt}"

        # Check that ordinals if present increase left-to-right/top-to-bottom in DOM order
        ordinals = page.locator('#gallery .tile-ordinal')
        vals = []
        for i in range(ordinals.count()):
            t = ordinals.nth(i).inner_text().strip()
            try:
                vals.append(int(t))
            except Exception:
                continue

        if vals:
            assert vals == sorted(vals), f"ordinals not sorted in DOM order: {vals}"

        context.close()
        browser.close()
