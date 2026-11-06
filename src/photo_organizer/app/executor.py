"""Applies an approved set of Suggestions (architecture.md "Operation executor").

This is the only module in the slice allowed to call the filesystem adapter
with a Suggestion. It is called once, after the UI approval gate, with
exactly the suggestions the user approved (FR-6: "the approved plan is the
exact set of actions the app attempts"). One file's failure never stops the
rest (FR-8).

Journaling to SQLite and undo are deferred past this thin slice
(architecture.md Open Decisions / this build's scoping) — results are
returned in memory for the UI to display.
"""

from __future__ import annotations

from collections.abc import Callable

from photo_organizer.domain.models import ActionState, OperationResult, Suggestion
from photo_organizer.filesystem.adapter import (
    DestinationExistsError,
    SourceChangedError,
    SourceFingerprint,
    move_file,
)


def execute_plan(
    approved: list[Suggestion],
    *,
    on_result: Callable[[OperationResult], None] | None = None,
) -> list[OperationResult]:
    results: list[OperationResult] = []

    for suggestion in approved:
        if not suggestion.included:
            continue

        result = _execute_one(suggestion)
        results.append(result)
        if on_result is not None:
            on_result(result)

    return results


def _execute_one(suggestion: Suggestion) -> OperationResult:
    if suggestion.has_blocking_warning:
        return OperationResult(
            suggestion=suggestion,
            state=ActionState.SKIPPED,
            message="Skipped: unresolved blocking warning (collision or read error).",
        )

    # Compare against the fingerprint captured at scan time (carried on the
    # suggestion), not one re-read right now -- re-reading "now" would always
    # match itself and could never detect a change since the scan.
    expected = SourceFingerprint(size=suggestion.expected_size, modified_time_ns=suggestion.expected_mtime_ns)

    try:
        move_file(suggestion.source, suggestion.destination, expected)
    except SourceChangedError as exc:
        return OperationResult(suggestion=suggestion, state=ActionState.SKIPPED, message=str(exc))
    except DestinationExistsError as exc:
        return OperationResult(suggestion=suggestion, state=ActionState.SKIPPED, message=str(exc))
    except OSError as exc:
        return OperationResult(
            suggestion=suggestion,
            state=ActionState.FAILED,
            message=f"Move failed: {exc}",
        )

    return OperationResult(suggestion=suggestion, state=ActionState.SUCCEEDED, message="Moved.")
