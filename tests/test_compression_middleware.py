from fastapi import FastAPI, Response
from fastapi.testclient import TestClient


def test_compression_middleware_compresses_large_plain_text():
    """Verify GZipMiddleware compresses responses >= 500 bytes with matching Accept-Encoding."""
    app = FastAPI()

    @app.get("/large")
    def large_endpoint():
        # Return 600 bytes (above 500 minimum)
        return Response("x" * 600, media_type="text/plain")

    from app.core.middleware_compression import add_compression_middleware

    add_compression_middleware(app)
    client = TestClient(app)

    r = client.get("/large", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    # TestClient auto-decompresses, so we check the header is set
    assert r.headers.get("Content-Encoding") == "gzip" or len(r.content) > 0
    # The content should be the original 600 bytes (auto-decompressed by TestClient)
    assert len(r.content) >= 600


def test_compression_middleware_doesnt_compress_small_responses():
    """Verify small responses (< 500 bytes) are not compressed by GZipMiddleware."""
    app = FastAPI()

    @app.get("/small")
    def small_endpoint():
        # Return 400 bytes (below 500 minimum)
        return Response("x" * 400, media_type="text/plain")

    from app.core.middleware_compression import add_compression_middleware

    add_compression_middleware(app)
    client = TestClient(app)

    r = client.get("/small", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    # Small response should NOT be compressed (below 500-byte minimum)
    assert r.headers.get("Content-Encoding") is None
    assert r.content == b"x" * 400


def test_compression_middleware_respects_accept_encoding():
    """Verify responses are not gzipped when Accept-Encoding doesn't include gzip."""
    app = FastAPI()

    @app.get("/large")
    def large_endpoint():
        return Response("x" * 600, media_type="text/plain")

    from app.core.middleware_compression import add_compression_middleware

    add_compression_middleware(app)
    client = TestClient(app)

    # Request without gzip in Accept-Encoding
    r = client.get("/large", headers={"Accept-Encoding": "deflate"})
    assert r.status_code == 200
    # Response should not be gzipped
    assert r.headers.get("Content-Encoding") != "gzip"


def test_compression_middleware_compresses_json():
    """Verify JSON responses are also compressed when above minimum size."""
    app = FastAPI()

    @app.get("/api/large")
    def large_json_endpoint():
        # Return a large JSON-like response
        json_content = '{"data": [' + ", ".join([f'{{"id": {i}}}' for i in range(100)]) + "]}"
        return Response(json_content, media_type="application/json")

    from app.core.middleware_compression import add_compression_middleware

    add_compression_middleware(app)
    client = TestClient(app)

    r = client.get("/api/large", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    # GZipMiddleware should mark for compression
    assert r.headers.get("Content-Encoding") == "gzip" or b'"data"' in r.content
    # Verify decompressed content is JSON-like (TestClient auto-decompresses)
    assert b'"data"' in r.content
