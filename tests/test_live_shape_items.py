import logging

from app.api.live import _shape_live_items


def test_shape_live_items_supports_image_video_and_skips_unsupported():
    rows = [
        (1, "image/jpeg", "a.jpg"),
        (2, "video/mp4", "b.mp4"),
        (3, "application/pdf", "c.pdf"),
    ]

    out = _shape_live_items(rows, user_id=10, event_id=99, event_code="ABC123")

    assert len(out) == 2
    assert out[0]["type"] == "image"
    assert out[1]["type"] == "video"
    assert out[0]["src"].startswith("/media/10/99/a.jpg?code=ABC123")
    assert out[1]["src"].startswith("/media/10/99/b.mp4?code=ABC123")


def test_shape_live_items_logs_malformed_rows(caplog):
    rows = [
        (1, "image/jpeg", "ok.jpg"),
        ("bad-id", "image/jpeg", "oops.jpg"),
    ]

    with caplog.at_level(logging.WARNING, logger="audit"):
        out = _shape_live_items(rows, user_id=10, event_id=99, event_code="ABC123")

    assert len(out) == 1
    assert out[0]["src"].startswith("/media/10/99/ok.jpg?code=ABC123")
    assert "live.slideshow.shape_row_failed" in caplog.text
