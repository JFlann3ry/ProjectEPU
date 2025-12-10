"""Dependencies for FastAPI routes."""
from typing import Optional

from fastapi import Request

from app.services.s3_storage import S3StorageService


async def get_s3_service(request: Request) -> Optional[S3StorageService]:
    """Provide S3 storage service to routes (None if not configured)."""
    return getattr(request.app.state, "s3_service", None)
