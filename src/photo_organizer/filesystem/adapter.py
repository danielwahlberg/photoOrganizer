"""Owns the actual move/rename primitive (architecture.md "Filesystem adapter").

Only the executor calls this module. It never overwrites a destination and
it revalidates the source immediately before moving, per the Safety
Invariants in architecture.md.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


class DestinationExistsError(Exception):
    """Raised when the destination exists at move time (never overwrite)."""


class SourceChangedError(Exception):
    """Raised when the source no longer matches what was approved."""


@dataclass(frozen=True)
class SourceFingerprint:
    """Cheap identity check. architecture.md notes size/mtime aren't a unique
    identity but are useful; stronger checks (e.g. content hash) are a later
    enhancement, not required for this slice."""

    size: int
    modified_time_ns: int

    @classmethod
    def capture(cls, path: Path) -> "SourceFingerprint":
        stat = path.stat()
        return cls(size=stat.st_size, modified_time_ns=stat.st_mtime_ns)


def move_file(source: Path, destination: Path, expected: SourceFingerprint) -> None:
    """Move `source` to `destination`, creating parent folders as needed.

    Raises SourceChangedError if `source` no longer matches `expected`, or
    DestinationExistsError if something is already at `destination`. Both
    are checked immediately before the move to minimize the race window.
    """
    if not source.exists():
        raise SourceChangedError(f"Source no longer exists: {source}")

    current = SourceFingerprint.capture(source)
    if current != expected:
        raise SourceChangedError(f"Source changed since it was approved: {source}")

    if destination.exists():
        raise DestinationExistsError(f"Destination already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    # shutil.move handles same-volume renames atomically where the OS
    # supports it, and falls back to copy+remove across volumes. It does not
    # overwrite an existing destination file because we already verified
    # above that none exists; a race in that tiny window is a known,
    # documented limitation (architecture.md: "do not claim multi-file
    # operations are atomic").
    shutil.move(str(source), str(destination))
