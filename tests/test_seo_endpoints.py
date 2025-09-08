

def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "User-agent" in r.text
    assert "Sitemap:" in r.text


def test_sitemap_xml(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert r.text.startswith("<?xml")
    assert "<urlset" in r.text


def test_share_page_not_found(client):
    r = client.get("/e/does-not-exist")
    assert r.status_code in (200, 404)
