from datetime import datetime, timezone
from pathlib import Path

from photo_organizer.app.suggestion_engine import build_suggestions
from photo_organizer.domain.models import DateSource, ScanRecord
from photo_organizer.rules.naming import DateFolderRule


def _record(path: str, capture_date, date_source=DateSource.EXIF, error=None) -> ScanRecord:
    return ScanRecord(
        path=Path(path),
        size=123,
        modified_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        mtime_ns=0,
        capture_date=capture_date,
        date_source=date_source,
        error=error,
    )


def test_two_files_mapping_to_same_destination_are_automatically_numbered():
    # Two different source files (different folders) share a stem, so the
    # same {name}-based pattern would otherwise collide. As of US-16 this is
    # auto-resolved like any other in-batch collision, not blocked.
    rule = DateFolderRule(destination_root=Path("/dest"))
    records = [
        _record("/src/x/photo.jpg", datetime(2023, 7, 4, 10, 0, 0)),
        _record("/src/y/photo.jpg", datetime(2023, 7, 4, 10, 0, 0)),
    ]

    suggestions = build_suggestions(records, rule)

    assert not any(s.has_blocking_warning for s in suggestions)
    destinations = {s.destination for s in suggestions}
    assert destinations == {
        Path("/dest/2023/07/2023-07-04_photo.jpg"),
        Path("/dest/2023/07/2023-07-04_photo_2.jpg"),
    }


def test_unreadable_record_produces_blocking_excluded_suggestion():
    records = [_record("/src/broken.jpg", None, DateSource.UNKNOWN, error="truncated file")]
    rule = DateFolderRule(destination_root=Path("/dest"))

    suggestions = build_suggestions(records, rule)

    assert len(suggestions) == 1
    assert suggestions[0].has_blocking_warning
    assert suggestions[0].included is False


def test_filesystem_fallback_date_is_flagged_not_hidden():
    records = [_record("/src/a.jpg", datetime(2023, 1, 1), DateSource.FILESYSTEM_FALLBACK)]
    rule = DateFolderRule(destination_root=Path("/dest"))

    suggestions = build_suggestions(records, rule)

    assert any("filesystem date" in w for w in suggestions[0].warnings)


def test_same_second_photos_are_automatically_numbered_not_blocked():
    # Pattern with no {name}/{seq}, relying on time-of-day alone -- two
    # photos in the same second can't be told apart by the pattern itself.
    rule = DateFolderRule(destination_root=Path("/dest"), pattern="{hour}-{minute}-{second}{ext}")
    same_second = datetime(2023, 7, 4, 9, 0, 0)
    records = [
        _record("/src/a.jpg", same_second),
        _record("/src/b.jpg", same_second),
    ]

    suggestions = build_suggestions(records, rule)

    destinations = {s.destination for s in suggestions}
    assert destinations == {Path("/dest/09-00-00.jpg"), Path("/dest/09-00-00_2.jpg")}
    # Automatic, but not silent: exactly one row explains what happened, and
    # neither row is blocked from being applied.
    assert not any(s.has_blocking_warning for s in suggestions)
    numbered = [s for s in suggestions if s.destination == Path("/dest/09-00-00_2.jpg")]
    assert any("Automatically numbered (_2)" in w for w in numbered[0].warnings)


def test_three_way_same_second_collision_numbers_sequentially():
    rule = DateFolderRule(destination_root=Path("/dest"), pattern="{hour}-{minute}-{second}{ext}")
    same_second = datetime(2023, 7, 4, 9, 0, 0)
    records = [_record(f"/src/{n}.jpg", same_second) for n in ("a", "b", "c")]

    suggestions = build_suggestions(records, rule)

    destinations = {s.destination for s in suggestions}
    assert destinations == {
        Path("/dest/09-00-00.jpg"),
        Path("/dest/09-00-00_2.jpg"),
        Path("/dest/09-00-00_3.jpg"),
    }


def test_sequence_numbers_reset_per_capture_date():
    rule = DateFolderRule(destination_root=Path("/dest"), pattern="{year}/{seq}_{name}{ext}")
    records = [
        _record("/src/a.jpg", datetime(2023, 7, 4, 9, 0, 0)),
        _record("/src/b.jpg", datetime(2023, 7, 4, 15, 0, 0)),  # same date as a.jpg
        _record("/src/c.jpg", datetime(2023, 7, 5, 9, 0, 0)),  # different date
    ]

    suggestions = build_suggestions(records, rule)

    by_source = {s.source: s.destination for s in suggestions}
    assert by_source[Path("/src/a.jpg")] == Path("/dest/2023/0001_a.jpg")
    assert by_source[Path("/src/b.jpg")] == Path("/dest/2023/0002_b.jpg")
    assert by_source[Path("/src/c.jpg")] == Path("/dest/2023/0001_c.jpg")  # resets on the new date
