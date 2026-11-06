from pathlib import Path

from photo_organizer.app.executor import execute_plan
from photo_organizer.domain.models import ActionKind, ActionState, Suggestion


def _suggestion(source: Path, destination: Path) -> Suggestion:
    """Mirrors what suggestion_engine does: fingerprint the source now, as
    if this were scan time, so a later on-disk change can be detected."""
    stat = source.stat()
    return Suggestion(
        kind=ActionKind.RENAME_MOVE,
        source=source,
        destination=destination,
        rationale="test",
        expected_size=stat.st_size,
        expected_mtime_ns=stat.st_mtime_ns,
    )


def _suggestion_for_missing_source(source: Path, destination: Path) -> Suggestion:
    return Suggestion(
        kind=ActionKind.RENAME_MOVE,
        source=source,
        destination=destination,
        rationale="test",
        expected_size=0,
        expected_mtime_ns=0,
    )


def test_successful_move(tmp_path: Path):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"fake-image-bytes")
    destination = tmp_path / "2024" / "01" / "a.jpg"

    results = execute_plan([_suggestion(source, destination)])

    assert results[0].state == ActionState.SUCCEEDED
    assert destination.exists()
    assert not source.exists()


def test_never_overwrites_existing_destination(tmp_path: Path):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"source-bytes")
    destination = tmp_path / "dest.jpg"
    destination.write_bytes(b"pre-existing-bytes")

    results = execute_plan([_suggestion(source, destination)])

    assert results[0].state == ActionState.SKIPPED
    assert destination.read_bytes() == b"pre-existing-bytes"
    assert source.exists()  # untouched


def test_source_changed_after_approval_is_skipped_not_moved(tmp_path: Path):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"original-bytes")
    destination = tmp_path / "dest.jpg"
    suggestion = _suggestion(source, destination)

    # Simulate the file changing on disk between review and apply.
    import time

    time.sleep(0.01)
    source.write_bytes(b"changed-bytes-now-longer")

    results = execute_plan([suggestion])

    assert results[0].state == ActionState.SKIPPED
    assert not destination.exists()
    assert source.exists()


def test_one_failure_does_not_stop_remaining_actions(tmp_path: Path):
    good_source = tmp_path / "good.jpg"
    good_source.write_bytes(b"ok")
    good_destination = tmp_path / "out" / "good.jpg"

    missing_source = tmp_path / "missing.jpg"  # never created -> will fail revalidation
    missing_destination = tmp_path / "out" / "missing.jpg"

    suggestions = [
        _suggestion_for_missing_source(missing_source, missing_destination),
        _suggestion(good_source, good_destination),
    ]

    results = execute_plan(suggestions)

    assert results[0].state == ActionState.SKIPPED
    assert results[1].state == ActionState.SUCCEEDED
    assert good_destination.exists()


def test_blocking_warning_is_skipped_even_if_included(tmp_path: Path):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"ok")
    destination = tmp_path / "dest.jpg"
    suggestion = _suggestion(source, destination)
    suggestion.warnings.append("BLOCKING: collision")

    results = execute_plan([suggestion])

    assert results[0].state == ActionState.SKIPPED
    assert source.exists()
    assert not destination.exists()
