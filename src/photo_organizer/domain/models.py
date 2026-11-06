"""Core data concepts shared across scanning, suggestion, and execution.

These mirror architecture.md's "Core Data Concepts" section, trimmed to what
the current thin vertical slice needs. No filesystem mutation happens here;
these are plain data holders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class DateSource(str, Enum):
    """Where a scan record's capture date came from.

    Required so the UI can show provenance instead of presenting a guessed
    date as if it were authoritative (requirements.md FR-3).
    """

    EXIF = "exif"
    FILESYSTEM_FALLBACK = "filesystem_fallback"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ScanRecord:
    """A read-only fact sheet for one discovered file."""

    path: Path
    size: int
    modified_time: datetime
    mtime_ns: int
    capture_date: datetime | None
    date_source: DateSource
    error: str | None = None  # set when the file was unreadable; still reported, not hidden

    @property
    def is_readable(self) -> bool:
        return self.error is None


class ActionKind(str, Enum):
    RENAME_MOVE = "rename_move"
    # "remove" (quarantine) is part of the documented MVP scope but is not
    # implemented in this thin slice.


class ActionState(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class Suggestion:
    """A proposed, not-yet-applied action for one file.

    `included` is the user's review-time selection (requirements.md FR-5);
    it starts True and the UI toggles it per row.

    `expected_size`/`expected_mtime_ns` are captured at scan time and carried
    through review and approval so the executor can detect "changed since
    the scan" (FR-1/FR-7) by comparing against the state the user actually
    reviewed, not against a value re-read moments before the move (which
    would always match itself and defeat the check).
    """

    kind: ActionKind
    source: Path
    destination: Path
    rationale: str
    expected_size: int = 0
    expected_mtime_ns: int = 0
    warnings: list[str] = field(default_factory=list)
    included: bool = True
    state: ActionState = ActionState.PROPOSED

    @property
    def has_blocking_warning(self) -> bool:
        """Collisions and similar problems must block execution, not just be noted."""
        return any(w.startswith("BLOCKING:") for w in self.warnings)


@dataclass
class OperationResult:
    """Outcome of attempting one approved suggestion."""

    suggestion: Suggestion
    state: ActionState
    message: str = ""
