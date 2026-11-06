"""Capture-date extraction, isolated behind a narrow interface.

architecture.md calls for metadata parsing to live behind a metadata-reader
interface so a different backend (or RAW/HEIC support) can be swapped in
later without touching the scanner or suggestion engine. This module is that
interface for the "common formats only" decision (JPEG/PNG/TIFF/BMP/WEBP via
Pillow).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image, UnidentifiedImageError

from photo_organizer.domain.models import DateSource

_EXIF_DATETIME_TAGS = (
    "DateTimeOriginal",
    "DateTimeDigitized",
    "DateTime",
)
_EXIF_TAG_IDS = {v: k for k, v in ExifTags.TAGS.items()}


def read_capture_date(path: Path, filesystem_modified_time: datetime) -> tuple[datetime | None, DateSource]:
    """Return (capture_date, provenance). Never raises for an unreadable image.

    Falls back to the filesystem modified time only as a clearly-marked
    fallback (requirements.md FR-3) — never silently presented as EXIF data.
    """
    exif_date = _read_exif_date(path)
    if exif_date is not None:
        return exif_date, DateSource.EXIF
    if filesystem_modified_time is not None:
        return filesystem_modified_time, DateSource.FILESYSTEM_FALLBACK
    return None, DateSource.UNKNOWN


def _read_exif_date(path: Path) -> datetime | None:
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            for tag_name in _EXIF_DATETIME_TAGS:
                tag_id = _EXIF_TAG_IDS.get(tag_name)
                if tag_id is None:
                    continue
                raw = exif.get(tag_id)
                if not raw:
                    continue
                parsed = _parse_exif_datetime(raw)
                if parsed is not None:
                    return parsed
    except (UnidentifiedImageError, OSError, ValueError):
        # Unreadable/corrupt file or unparsable EXIF: treat as "no EXIF date"
        # rather than raising. The scanner reports read errors separately.
        return None
    return None


def _parse_exif_datetime(raw: str) -> datetime | None:
    # Standard EXIF format: "YYYY:MM:DD HH:MM:SS"
    try:
        return datetime.strptime(raw.strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
