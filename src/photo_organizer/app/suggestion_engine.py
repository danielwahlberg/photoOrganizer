"""Turn scan records into reviewable Suggestions (architecture.md "Suggestion engine").

Never touches the filesystem. Handles two collision cases requirements.md
FR-7 requires to be visible *before* approval:
- A proposed destination that already exists on disk (pre-existing file):
  still a "BLOCKING:" warning -- the executor and UI refuse to run it until
  the user resolves or excludes the row. This file may be unrelated to the
  one already there, so the app never guesses.
- Two proposed destinations in this batch landing on the same path
  (requirements.md US-16, e.g. two photos a pattern using only
  {hour}{minute}{second} can't tell apart because they share the same
  second): automatically resolved by appending an unpadded _2, _3, ...
  suffix to the later file(s), and called out in that suggestion's
  warnings so the renumbering is visible, not silent. This is safe to do
  automatically because it only ever affects files already selected in
  this same plan -- it can't touch a file outside the batch, which is what
  the pre-existing-file case above still blocks on.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from photo_organizer.domain.models import ActionKind, DateSource, ScanRecord, Suggestion
from photo_organizer.rules.naming import DateFolderRule


def build_suggestions(records: list[ScanRecord], rule: DateFolderRule) -> list[Suggestion]:
    unreadable = [r for r in records if not r.is_readable]
    readable = [r for r in records if r.is_readable]

    sequences = _assign_daily_sequences(readable)
    raw_destinations = [rule.propose_destination(r, sequence=sequences[id(r)]) for r in readable]
    proposed_destinations, collision_notes = _resolve_in_batch_collisions(raw_destinations)

    # Safety net only: after resolution above, no two destinations should
    # still collide. If one somehow does (e.g. the auto-numbered name
    # itself happened to already be taken by an unrelated file), fall back
    # to the original blocking behavior rather than silently guessing.
    destination_counts = Counter(_normalized(p) for p in proposed_destinations)

    suggestions: list[Suggestion] = []
    for record, destination, collision_note in zip(readable, proposed_destinations, collision_notes):
        warnings: list[str] = []

        if record.date_source == DateSource.FILESYSTEM_FALLBACK:
            warnings.append("No capture-date metadata found; used the file's filesystem date instead.")
        elif record.date_source == DateSource.UNKNOWN:
            warnings.append("No usable date found; filed under 'unknown_date'.")

        if collision_note is not None:
            warnings.append(collision_note)

        if destination_counts[_normalized(destination)] > 1:
            warnings.append("BLOCKING: Another selected file would move to the same destination.")

        if destination.exists():
            warnings.append("BLOCKING: A file already exists at the destination.")

        rationale = _rationale_for(record)

        suggestions.append(
            Suggestion(
                kind=ActionKind.RENAME_MOVE,
                source=record.path,
                destination=destination,
                rationale=rationale,
                expected_size=record.size,
                expected_mtime_ns=record.mtime_ns,
                warnings=warnings,
            )
        )

    for record in unreadable:
        suggestions.append(
            Suggestion(
                kind=ActionKind.RENAME_MOVE,
                source=record.path,
                destination=record.path,
                rationale="Could not read this file during scan.",
                warnings=[f"BLOCKING: {record.error}"],
                included=False,
            )
        )

    return suggestions


def _rationale_for(record: ScanRecord) -> str:
    if record.date_source == DateSource.EXIF:
        return f"Capture date {record.capture_date:%Y-%m-%d} read from image metadata."
    if record.date_source == DateSource.FILESYSTEM_FALLBACK:
        return f"No metadata date; using filesystem modified date {record.capture_date:%Y-%m-%d}."
    return "No date available from metadata or filesystem."


def _normalized(path: Path) -> str:
    return str(path).lower()


def _resolve_in_batch_collisions(destinations: list[Path]) -> tuple[list[Path], list[str | None]]:
    """Disambiguate destinations that collide within this same batch.

    requirements.md US-16: when a pattern (most often one using only
    {hour}{minute}{second}, with no {name}/{seq}) isn't fine-grained enough
    to tell two files in the batch apart, append an unpadded _2, _3, ...
    suffix to each file after the first that would otherwise land on the
    same path. Returns (adjusted destinations, a per-item note or None),
    parallel to the input list, in the same order.
    """
    seen_counts: dict[str, int] = {}
    reserved: set[str] = set()
    resolved: list[Path] = []
    notes: list[str | None] = []

    for destination in destinations:
        key = _normalized(destination)
        seen_counts[key] = seen_counts.get(key, 0) + 1
        if seen_counts[key] == 1 and key not in reserved:
            reserved.add(key)
            resolved.append(destination)
            notes.append(None)
            continue

        suffix = seen_counts[key]
        while True:
            candidate = destination.with_name(f"{destination.stem}_{suffix}{destination.suffix}")
            candidate_key = _normalized(candidate)
            if candidate_key not in reserved:
                break
            suffix += 1

        reserved.add(candidate_key)
        resolved.append(candidate)
        notes.append(
            f"Automatically numbered (_{suffix}) because another file in this batch "
            "would otherwise move to the same destination."
        )

    return resolved, notes


def _assign_daily_sequences(readable: list[ScanRecord]) -> dict[int, int]:
    """1-based position of each record within its capture-date group
    (requirements.md US-15): the first file on a given date gets 1, the
    next file on that same date gets 2, and so on. Records with no capture
    date don't use the pattern at all (they go to 'unknown_date'), so their
    sequence value is never read; 1 is assigned as a harmless placeholder.

    Keyed by id(record) rather than the record itself: ScanRecord is a
    frozen dataclass, so two distinct files scanned with identical
    size/dates would otherwise collide as the same dict key.
    """
    counters: dict[object, int] = defaultdict(int)
    sequences: dict[int, int] = {}
    for record in readable:
        group_key = record.capture_date.date() if record.capture_date is not None else None
        counters[group_key] += 1
        sequences[id(record)] = counters[group_key]
    return sequences
