from datetime import datetime, timezone
from pathlib import Path

import pytest

from photo_organizer.domain.models import DateSource, ScanRecord
from photo_organizer.rules.naming import DateFolderRule, InvalidPatternError, validate_pattern


def _record(path: str, capture_date, date_source=DateSource.EXIF) -> ScanRecord:
    return ScanRecord(
        path=Path(path),
        size=123,
        modified_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        mtime_ns=0,
        capture_date=capture_date,
        date_source=date_source,
    )


def test_date_folder_rule_builds_year_month_path():
    rule = DateFolderRule(destination_root=Path("/dest"))
    record = _record("/src/IMG_0001.JPG", datetime(2023, 7, 4, 10, 30, 0))

    destination = rule.propose_destination(record)

    assert destination == Path("/dest/2023/07/2023-07-04_IMG_0001.jpg")


def test_date_folder_rule_falls_back_to_unknown_date_folder():
    rule = DateFolderRule(destination_root=Path("/dest"))
    record = _record("/src/no_date.png", None, DateSource.UNKNOWN)

    destination = rule.propose_destination(record)

    assert destination == Path("/dest/unknown_date/no_date.png")


def test_custom_pattern_is_honored():
    rule = DateFolderRule(destination_root=Path("/dest"), pattern="flat/{year}-{month}-{day}_{name}{ext}")
    record = _record("/src/IMG_0001.JPG", datetime(2023, 7, 4, 10, 30, 0))

    destination = rule.propose_destination(record)

    assert destination == Path("/dest/flat/2023-07-04_IMG_0001.jpg")


@pytest.mark.parametrize(
    "pattern",
    [
        "",
        "   ",
        "{year}/{month}/{day}",  # missing {name} and {seq}
        "{unknown_placeholder}/{name}",
        "/{year}/{name}",  # not relative
        "../{year}/{name}",
    ],
)
def test_invalid_patterns_are_rejected(pattern: str):
    with pytest.raises(InvalidPatternError):
        validate_pattern(pattern)


def test_valid_pattern_passes_validation():
    validate_pattern("{year}/{month}/{year}-{month}-{day}_{name}{ext}")  # should not raise


def test_seq_alone_satisfies_the_distinguishing_placeholder_requirement():
    # No {name} at all -- {seq} is enough (US-15).
    validate_pattern("{year}/{month}/{day}_{seq}{ext}")


def test_sequence_number_is_formatted_and_zero_padded():
    rule = DateFolderRule(destination_root=Path("/dest"), pattern="{year}/{seq}_{name}{ext}")
    record = _record("/src/a.jpg", datetime(2023, 7, 4, 10, 0, 0))

    destination = rule.propose_destination(record, sequence=7)

    assert destination == Path("/dest/2023/0007_a.jpg")


def test_sequence_defaults_to_one_when_caller_omits_it():
    rule = DateFolderRule(destination_root=Path("/dest"), pattern="{year}/{seq}_{name}{ext}")
    record = _record("/src/a.jpg", datetime(2023, 7, 4, 10, 0, 0))

    destination = rule.propose_destination(record)

    assert destination == Path("/dest/2023/0001_a.jpg")


def test_two_digit_year_and_time_of_day_placeholders():
    rule = DateFolderRule(
        destination_root=Path("/dest"),
        pattern="{yy}/{hour}-{minute}-{second}_{name}{ext}",
    )
    record = _record("/src/a.jpg", datetime(2023, 7, 4, 14, 5, 9))

    destination = rule.propose_destination(record)

    assert destination == Path("/dest/23/14-05-09_a.jpg")


def test_full_time_of_day_alone_satisfies_the_distinguishing_placeholder_requirement():
    # No {name} and no {seq} -- {hour}+{minute}+{second} together are enough (US-16);
    # a same-second collision is handled by the suggestion engine, not here.
    validate_pattern("{year}/{month}/{day}/{hour}-{minute}-{second}{ext}")


@pytest.mark.parametrize(
    "pattern",
    [
        "{hour}-{minute}{ext}",  # missing {second}: not the full time-of-day
        "{hour}{ext}",
    ],
)
def test_partial_time_of_day_does_not_satisfy_requirement(pattern: str):
    with pytest.raises(InvalidPatternError):
        validate_pattern(pattern)
