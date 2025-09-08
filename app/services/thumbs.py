import glob
import os
import subprocess
from typing import Iterable


def _thumbs_dir(user_id: int, event_id: int) -> str:
    return os.path.join("storage", str(user_id), str(event_id), "thumbnails")


def image_thumb_path(user_id: int, event_id: int, file_id: int, width: int) -> str:
    return os.path.join(_thumbs_dir(user_id, event_id), f"{file_id}_{width}.jpg")


def ensure_image_thumbnail(orig_path: str, out_path: str, width: int) -> bool:
    try:
        from PIL import Image, ImageOps  # type: ignore

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with Image.open(orig_path) as im:
            im = ImageOps.exif_transpose(im)
            # Avoid upscaling
            w = min(int(width), int(im.width)) if im.width else int(width)
            if w <= 0:
                w = int(width)
            ratio = w / float(max(1, im.width))
            new_size = (w, max(1, int(im.height * ratio)))
            im = im.convert("RGB").resize(new_size, Image.Resampling.LANCZOS)
            tmp = out_path + ".tmp"
            im.save(tmp, format="JPEG", quality=82, optimize=True, progressive=True)
            os.replace(tmp, out_path)
        return True
    except Exception:
        return False


def ensure_video_poster(orig_path: str, out_path: str, width: int) -> bool:
    """Use ffmpeg if available to extract a poster frame and resize to width.
    Requires ffmpeg on PATH. Returns True if poster created.
    """
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        # Extract at 1s to skip black frames; scale maintaining aspect (even heights)
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            "1",
            "-i",
            orig_path,
            "-vframes",
            "1",
            "-vf",
            f"scale={int(width)}:-2",
            out_path,
        ]
        # Suppress ffmpeg output
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return os.path.exists(out_path)
    except Exception:
        return False


def cleanup_thumbnails(user_id: int, event_id: int, file_id: int) -> None:
    """Remove all persisted thumbnails for a file id."""
    tdir = _thumbs_dir(user_id, event_id)
    pattern = os.path.join(tdir, f"{file_id}_*.jpg")
    for p in glob.glob(pattern):
        try:
            os.remove(p)
        except Exception:
            pass


def generate_all_thumbs_for_file(
    user_id: int,
    event_id: int,
    file_id: int,
    file_type: str,
    file_name: str,
    widths: Iterable[int] = (480, 720, 960, 1440),
) -> None:
    """Generate image thumbnails or video posters for desired widths."""
    base = os.path.join("storage", str(user_id), str(event_id))
    orig_path = os.path.join(base, file_name)
    if not os.path.exists(orig_path):
        return
    is_image = (file_type or "").startswith("image")
    is_video = (file_type or "").startswith("video")
    for w in widths:
        out_path = image_thumb_path(user_id, event_id, file_id, int(w))
        if is_image:
            if os.path.exists(out_path):
                continue
            ensure_image_thumbnail(orig_path, out_path, int(w))
        elif is_video:
            if os.path.exists(out_path):
                continue
            ensure_video_poster(orig_path, out_path, int(w))