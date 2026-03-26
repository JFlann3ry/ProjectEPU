import re

from app.models.logging import AppErrorLog


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]*)"', html)
    assert m, "csrf_token input not found"
    return m.group(1)


def test_contact_email_failure_is_logged_and_redirects(client, db_session, monkeypatch, caplog):
    async def _boom(**kwargs):
        raise RuntimeError("smtp unavailable")

    monkeypatch.setattr("app.api.support.send_support_email", _boom)

    r_get = client.get("/contact")
    assert r_get.status_code == 200
    csrf = _extract_csrf(r_get.text)

    caplog.set_level("ERROR", logger="audit")

    r_post = client.post(
        "/contact",
        data={
            "name": "Jane Host",
            "email": "jane@example.com",
            "topic": "Technical issue",
            "message": "Upload failed",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )

    assert r_post.status_code == 303
    assert r_post.headers.get("location") == "/contact/sent"

    rows = (
        db_session.query(AppErrorLog)
        .filter(AppErrorLog.Path == "/contact", AppErrorLog.Message == "support.email.send_failed")
        .all()
    )
    assert rows, "expected AppErrorLog row for support email failure"
    assert any((row.RequestID or "") for row in rows)

    assert "support.email.send_failed" in caplog.text


def test_contact_page_uses_extracted_page_script(client):
    r = client.get("/contact")

    assert r.status_code == 200
    assert "js/pages/contact.js" in r.text
    assert "var sel = document.getElementById('contact_topic');" not in r.text
