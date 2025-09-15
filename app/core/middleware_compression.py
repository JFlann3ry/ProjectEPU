from starlette.middleware.gzip import GZipMiddleware


# This is a simple wrapper for clarity and future extension if needed.
def add_compression_middleware(app):
    app.add_middleware(GZipMiddleware, minimum_size=500)
