from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_faq_page_renders():
    r = client.get("/faq")
    assert r.status_code == 200
    assert "Frequently Asked Questions" in r.text
    # Basic accordion structure
    assert "accordion-item" in r.text
    assert "accordion-header" in r.text
    assert "accordion-panel" in r.text


def test_footer_has_faq_link():
    r = client.get("/login")
    assert r.status_code == 200
    assert ">FAQ<" in r.text
