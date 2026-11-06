"""Read-only folder enumeration (architecture.md "Scanner" component).

Safety invariants honored here:
- Never modifies files.
- Never follows directory symlinks (requirements.md Safety And Data
  Integrity Requirements).
- One unreadable file produces a ScanRecord with `error` set; it does not
  abort the scan.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from photo_organizer.domain.models import DateSource, ScanRecord
from photo_organizer.scanning.metadata import read_capture_date

# "Common formats only" per the first-build decision. RAW/HEIC are a
# separate, still-open decision (architecture.md Open Decisions) and would
# be added here behind the same metadata-reader interface.
SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"})


class ScanCancelled(Exception):
    """Raised internally to stop a scan early when the caller requests cancellation."""


def scan_folder(
    root: Path,
    *,
    should_cancel: callable | None = None,
    on_progress: callable | None = None,
) -> tuple[list[ScanRecord], int]:
    """Enumerate supported image files under `root`.

    Returns (records, skipped_other_count). Directory symlinks are not
    followed. `should_cancel()` is polled between files so a long scan can
    be stopped (FR-1); `on_progress(count)` is called after each file for a
    responsive UI.
    """
    records: list[ScanRecord] = []
    skipped_other_count = 0

    try:
        for entry in _walk_no_symlinks(root):
            if should_cancel is not None and should_cancel():
                raise ScanCancelled()

            if entry.suffix.lower() not in SUPPORTED_EXTENSIONS:
                skipped_other_count += 1
                continue

            records.append(_scan_one(entry))
            if on_progress is not None:
                on_progress(len(records) + skipped_other_count)
    except ScanCancelled:
        pass

    return records, skipped_other_count


def _scan_one(path: Path) -> ScanRecord:
    try:
        stat = path.stat()
    except OSError as exc:
        return ScanRecord(
            path=path,
            size=0,
            modified_time=datetime.now(tz=timezone.utc),
            mtime_ns=0,
            capture_date=None,
            date_source=DateSource.UNKNOWN,
            error=f"Could not read file info: {exc}",
        )

    modified_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    capture_date, date_source = read_capture_date(path, modified_time)

    return ScanRecord(
        path=path,
        size=stat.st_size,
        modified_time=modified_time,
        mtime_ns=stat.st_mtime_ns,
        capture_date=capture_date,
        date_source=date_source,
        error=None,
    )


def _walk_no_symlinks(root: Path) -> Iterator[Path]:
    """Like Path.rglob but never follows symlinks at all.

    requirements.md requires directory symlinks to never be followed, and
    file-symlink behavior to be explicit and consistent. This slice's
    explicit choice: skip symlinks entirely (file or directory) rather than
    read through them, since the "stable file identity" guarantees elsewhere
    in the design assume a real file on disk.
    """
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return
    for entry in entries:
        if entry.is_symlink():
            continue
        if entry.is_dir():
            yield from _walk_no_symlinks(entry)
        elif entry.is_file():
            yield entry
