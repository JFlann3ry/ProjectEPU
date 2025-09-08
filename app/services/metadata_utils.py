import hashlib
import json
import re
import subprocess
from typing import Any, Dict

import piexif
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from PIL import Image


def extract_image_metadata(file_path) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    try:
        img = Image.open(file_path)
        exif_data = piexif.load(img.info.get("exif", b""))
        # DateTimeOriginal
        dt = exif_data["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
        if dt:
            dt_str = dt.decode()
            # Convert 'YYYY:MM:DD HH:MM:SS' to 'YYYY-MM-DD HH:MM:SS'
            metadata["datetime_taken"] = dt_str.replace(":", "-", 2) if dt_str else None
        else:
            metadata["datetime_taken"] = None
        # GPS
        gps = exif_data.get("GPS", {})

        def get_gps(coord, ref):
            if not coord or not ref:
                return None
            d, m, s = [x[0] / x[1] for x in coord]
            val = d + m / 60 + s / 3600
            if ref in [b"S", b"W"]:
                val = -val
            return val

        metadata["gps_lat"] = get_gps(
            gps.get(piexif.GPSIFD.GPSLatitude), gps.get(piexif.GPSIFD.GPSLatitudeRef)
        )
        metadata["gps_long"] = get_gps(
            gps.get(piexif.GPSIFD.GPSLongitude), gps.get(piexif.GPSIFD.GPSLongitudeRef)
        )
    except Exception:
        metadata["datetime_taken"] = None
        metadata["gps_lat"] = None
        metadata["gps_long"] = None
    # Checksum
    try:
        with open(file_path, "rb") as f:
            metadata["checksum"] = hashlib.sha256(f.read()).hexdigest()
    except Exception:
        metadata["checksum"] = None
    return metadata


# For video files, use hachoir (ffmpeg is more complex to bundle)


def extract_video_metadata(file_path) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "datetime_taken": None,
        "gps_lat": None,
        "gps_long": None,
        "checksum": None,
    }
    # Always compute checksum
    try:
        with open(file_path, "rb") as f:
            metadata["checksum"] = hashlib.sha256(f.read()).hexdigest()
    except Exception:
        metadata["checksum"] = None

    # Helper: parse ISO 6709 like +37.3349-122.0090+061.000/
    def parse_iso6709(val: str):
        try:
            m = re.match(
                r"^(?P<lat>[+\-]\d+(?:\.\d+)?)(?P<long>[+\-]\d+(?:\.\d+)?)(?P<alt>[+\-]\d+(?:\.\d+)?)?/?$",
                val.strip(),
            )
            if not m:
                return None, None
            lat = float(m.group("lat"))
            lon = float(m.group("long"))
            return lat, lon
        except Exception:
            return None, None

    # Helper: search generic lat/long in free-form tag strings
    def parse_loose_latlon(val: str):
        try:
            # Prefer comma-separated then space-separated decimals
            m = re.search(r"([+\-]?\d{1,2}(?:\.\d+)?)[,;\s]+([+\-]?\d{1,3}(?:\.\d+)?)", val)
            if not m:
                return None, None
            lat = float(m.group(1))
            lon = float(m.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
            return None, None
        except Exception:
            return None, None

    # Try ffprobe (if available) — best support for MP4/MOV QuickTime tags
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_entries",
                "format:format_tags:stream_tags",
                file_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        data = json.loads(proc.stdout or "{}")
        fmt = data.get("format", {}) or {}
        fmt_tags = fmt.get("tags", {}) or {}
        streams = data.get("streams", []) or []

        # Date/time
        dt = fmt_tags.get("creation_time") or fmt_tags.get("com.apple.quicktime.creationdate")
        if not dt:
            # look in streams
            for s in streams:
                t = (s.get("tags") or {}).get("creation_time")
                if t:
                    dt = t
                    break
        if dt:
            metadata["datetime_taken"] = str(dt)

        # GPS/location candidates
        def try_extract_from_tags(tags: dict):
            if not tags:
                return None, None
            # Apple QuickTime ISO6709
            val = (
                tags.get("com.apple.quicktime.location.ISO6709")
                or tags.get("location")
                or tags.get("location-eng")
            )
            if val:
                lat, lon = parse_iso6709(val)
                if lat is not None and lon is not None:
                    return lat, lon
                lat, lon = parse_loose_latlon(val)
                if lat is not None and lon is not None:
                    return lat, lon
            # Some devices store as separate keys
            lat_key = None
            lon_key = None
            for k in tags.keys():
                lk = k.lower()
                if not lat_key and ("latitude" in lk or lk.endswith(".lat")):
                    lat_key = k
                if not lon_key and (
                    "longitude" in lk or lk.endswith(".lon") or lk.endswith(".long")
                ):
                    lon_key = k
            if lat_key and lon_key:
                try:
                    return float(str(tags[lat_key])), float(str(tags[lon_key]))
                except Exception:
                    pass
            return None, None

        lat, lon = try_extract_from_tags(fmt_tags)
        if lat is None or lon is None:
            for s in streams:
                tlat, tlon = try_extract_from_tags(s.get("tags") or {})
                if tlat is not None and tlon is not None:
                    lat, lon = tlat, tlon
                    break
        if lat is not None and lon is not None:
            metadata["gps_lat"] = lat
            metadata["gps_long"] = lon
            return metadata
    except Exception:
        # ffprobe not available or failed — proceed to hachoir fallback
        pass

    # Fallback: hachoir (limited GPS support)
    try:
        parser = createParser(file_path)
        if not parser:
            return metadata
        metadata_obj = extractMetadata(parser)
        if metadata_obj:
            dt = metadata_obj.get("creation_date")
            metadata["datetime_taken"] = str(dt) if dt else metadata["datetime_taken"]
    except Exception:
        pass
    return metadata
