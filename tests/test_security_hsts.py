from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.core.middleware_security import SecurityHeadersMiddleware


def test_hsts_header_is_emitted_for_https_html_when_prod_only_enabled():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, prod_only=True)

    @app.get("/")
    def home():
        return Response("<html><body>ok</body></html>", media_type="text/html")

    client = TestClient(app)
    r = client.get("/", headers={"x-forwarded-proto": "https"})

    assert r.status_code == 200
    assert (
        r.headers.get("strict-transport-security") == "max-age=63072000; includeSubDomains; preload"
    )


def test_hsts_header_not_emitted_for_non_https_requests():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, prod_only=True)

    @app.get("/")
    def home():
        return Response("<html><body>ok</body></html>", media_type="text/html")

    client = TestClient(app)
    r = client.get("/")

    assert r.status_code == 200
    assert "strict-transport-security" not in r.headers
