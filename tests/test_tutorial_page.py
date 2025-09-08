from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_tutorial_page_renders_and_has_steps():
    r = client.get("/tutorial")
    assert r.status_code == 200
    assert "How to upload as a guest" in r.text
    assert "Screenshot 1" in r.text
    assert "Screenshot 6" in r.text


def test_footer_has_tutorial_link():
    r = client.get("/login")
    assert r.status_code == 200
    assert ">Tutorial<" in r.text
