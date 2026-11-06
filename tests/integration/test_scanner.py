from pathlib import Path

from photo_organizer.scanning.scanner import scan_folder


def test_scan_skips_unsupported_files_and_counts_them(tmp_path: Path):
    (tmp_path / "photo.jpg").write_bytes(b"not-a-real-jpeg-but-has-the-extension")
    (tmp_path / "notes.txt").write_text("not a photo")

    records, skipped_other = scan_folder(tmp_path)

    assert len(records) == 1
    assert records[0].path.name == "photo.jpg"
    assert skipped_other == 1


def test_scan_does_not_modify_files(tmp_path: Path):
    photo = tmp_path / "photo.png"
    original_bytes = b"fake-png-bytes"
    photo.write_bytes(original_bytes)
    original_mtime = photo.stat().st_mtime_ns

    scan_folder(tmp_path)

    assert photo.read_bytes() == original_bytes
    assert photo.stat().st_mtime_ns == original_mtime


def test_scan_does_not_follow_directory_symlinks(tmp_path: Path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "hidden.jpg").write_bytes(b"data")

    link_dir = tmp_path / "linked"
    try:
        link_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        import pytest

        pytest.skip("Creating symlinks requires elevated privileges on this system.")

    records, _ = scan_folder(tmp_path)

    found_paths = {r.path for r in records}
    assert real_dir / "hidden.jpg" not in found_paths
    # The real (non-symlinked) copy is still found when scanning its own parent directly.
    direct_records, _ = scan_folder(real_dir)
    assert len(direct_records) == 1
