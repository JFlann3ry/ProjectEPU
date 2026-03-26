from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.services.mime_utils import is_allowed_mime


@dataclass
class StagedUpload:
    temp_path: str
    size_bytes: int
    sniffed_mime: str
    allowed: bool


class UploadSizeExceeded(Exception):
    def __init__(self, size_bytes: int, max_bytes: int):
        super().__init__(f"upload exceeded max size {max_bytes} bytes")
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


def cleanup_temp_upload(path: str | None) -> None:
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


async def spool_upload_to_temp(
    upload: UploadFile,
    *,
    allowed_prefixes: tuple[str, ...] = ("image/", "video/"),
    max_bytes: int = 0,
    sniff_bytes_limit: int = 65_536,
    chunk_size: int = 1_048_576,
) -> StagedUpload:
    suffix = Path(getattr(upload, "filename", "") or "upload.bin").suffix
    temp_path = ""
    size_bytes = 0
    sniff = bytearray()

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            while True:
                chunk = await upload.read(chunk_size)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if max_bytes and size_bytes > max_bytes:
                    raise UploadSizeExceeded(size_bytes=size_bytes, max_bytes=max_bytes)
                if len(sniff) < sniff_bytes_limit:
                    remaining = sniff_bytes_limit - len(sniff)
                    sniff.extend(chunk[:remaining])
                tmp.write(chunk)

        allowed, sniffed_mime = is_allowed_mime(
            bytes(sniff),
            allowed_prefixes=allowed_prefixes,
            fallback_content_type=getattr(upload, "content_type", None),
        )
        return StagedUpload(
            temp_path=temp_path,
            size_bytes=size_bytes,
            sniffed_mime=sniffed_mime,
            allowed=allowed,
        )
    except Exception:
        cleanup_temp_upload(temp_path)
        raise
