"""The organization rule this slice implements: a user-editable, date-based pattern.

requirements.md US-14 resolves architecture.md's "Default and custom
organization rules" open decision: users can edit the active pattern, using
placeholders, rather than being stuck with a single hardcoded layout. Only
one pattern is active at a time (no named/saved presets yet — that remains
an open decision).

Written so a future second *kind* of rule could be added later without
changing the suggestion engine's contract (a rule is just a
ScanRecord -> relative Path function).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from photo_organizer.domain.models import ScanRecord
from pathlib import Path

_ALLOWED_PLACEHOLDERS = frozenset(
    {"year", "yy", "month", "day", "hour", "minute", "second", "name", "ext", "seq"}
)
_PLACEHOLDER_RE = re.compile(r"\{(\w*)\}")

DEFAULT_PATTERN = "{year}/{month}/{year}-{month}-{day}_{name}{ext}"

# {seq} resets each calendar day (requirements.md US-15): the first photo
# captured on a given date is 0001, the next on that same date is 0002, and
# so on. It is formatted at this fixed zero-padded width.
_SEQUENCE_WIDTH = 4

# Placeholders that, together, are fine-grained enough to usually
# distinguish files on their own (requirements.md US-16): a pattern using
# the full time-of-day doesn't also need {name} or {seq}, because any
# leftover same-second collision is caught and auto-numbered by the
# suggestion engine (see app/suggestion_engine._resolve_in_batch_collisions).
_TIME_OF_DAY_PLACEHOLDERS = ("{hour}", "{minute}", "{second}")

#: Human-readable legend for every placeholder, used both for the UI's
#: hover tooltip and for validation error messages. Keeping it as data
#: (rather than scattering placeholder descriptions across the UI) means
#: the UI and the validator can't drift out of sync about what's allowed.
PLACEHOLDER_LEGEND: tuple[tuple[str, str], ...] = (
    ("{year}", "4-digit year, e.g. 2023"),
    ("{yy}", "2-digit year, e.g. 23"),
    ("{month}", "2-digit month, 01-12"),
    ("{day}", "2-digit day, 01-31"),
    ("{hour}", "2-digit hour, 24h clock, 00-23"),
    ("{minute}", "2-digit minute, 00-59"),
    ("{second}", "2-digit second, 00-59"),
    ("{name}", "original filename, without its extension"),
    ("{ext}", "original file extension, e.g. .jpg"),
    ("{seq}", "4-digit number, resets each capture date: 0001, 0002, ..."),
)


class InvalidPatternError(ValueError):
    """A user-supplied pattern that can't be used safely or sensibly."""


def validate_pattern(pattern: str) -> None:
    """Raise InvalidPatternError with a user-facing message, or return None.

    Called both by the UI before a scan starts (US-14: "rejected ... before
    scanning runs") and by DateFolderRule itself as defense in depth.
    """
    if not pattern or not pattern.strip():
        raise InvalidPatternError("Pattern cannot be empty.")

    found = set(_PLACEHOLDER_RE.findall(pattern))
    unknown = found - _ALLOWED_PLACEHOLDERS
    if unknown:
        raise InvalidPatternError(
            f"Unknown placeholder(s): {', '.join(sorted(unknown))}. "
            f"Allowed placeholders: {', '.join(sorted(_ALLOWED_PLACEHOLDERS))}."
        )

    has_time_of_day = all(token in pattern for token in _TIME_OF_DAY_PLACEHOLDERS)
    if "{name}" not in pattern and "{seq}" not in pattern and not has_time_of_day:
        raise InvalidPatternError(
            "Pattern must include {name}, {seq}, or the full {hour}{minute}{second} "
            "time-of-day, so files keep a distinguishing name."
        )

    normalized = pattern.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("~"):
        raise InvalidPatternError("Pattern must be a relative path under the destination folder.")
    if any(segment == ".." for segment in normalized.split("/")):
        raise InvalidPatternError("Pattern cannot contain '..' path segments.")

    try:
        pattern.format(
            year="0000",
            yy="00",
            month="00",
            day="00",
            hour="00",
            minute="00",
            second="00",
            name="sample",
            ext=".jpg",
            seq="0001",
        )
    except (KeyError, IndexError, ValueError) as exc:
        raise InvalidPatternError(f"Pattern is not usable: {exc}") from exc


@dataclass(frozen=True)
class DateFolderRule:
    """Destination: <destination_root>/<pattern filled in from capture_date and filename>."""

    destination_root: Path
    pattern: str = DEFAULT_PATTERN
    unknown_date_folder_name: str = "unknown_date"

    def __post_init__(self) -> None:
        validate_pattern(self.pattern)

    def propose_destination(self, record: ScanRecord, sequence: int = 1) -> Path:
        """`sequence` is the 1-based position of this file within its
        capture-date group (requirements.md US-15), computed by the caller
        across the whole batch -- a single record carries no information
        about its siblings, so it cannot compute this itself. Callers that
        don't use {seq} in their pattern can ignore this parameter.
        """
        if record.capture_date is None:
            return self.destination_root / self.unknown_date_folder_name / record.path.name

        date = record.capture_date
        relative = self.pattern.format(
            year=f"{date.year:04d}",
            yy=f"{date.year % 100:02d}",
            month=f"{date.month:02d}",
            day=f"{date.day:02d}",
            hour=f"{date.hour:02d}",
            minute=f"{date.minute:02d}",
            second=f"{date.second:02d}",
            name=record.path.stem,
            ext=record.path.suffix.lower(),
            seq=f"{sequence:0{_SEQUENCE_WIDTH}d}",
        )
        return self.destination_root / relative
