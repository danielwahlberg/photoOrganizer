# Photo Organizer

See [requirements.md](requirements.md) and [architecture.md](architecture.md)
for the full product and design intent. This repo currently implements a
**thin vertical slice** of that design, not the full MVP.

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\python -m photo_organizer
```

Pick a source folder and a destination folder, click **Scan**, review the
table, uncheck anything you don't want, then **Approve & Apply**.

## Run the tests

```powershell
.\.venv\Scripts\python -m pytest -v
```

## Package it as a standalone app (no Python required on the target machine)

```powershell
.\.venv\Scripts\pip install -e ".[build]"
.\packaging\build_windows.ps1
```

This produces `dist\photo_organizer\` — a folder containing
`photo_organizer.exe` plus every dependency it needs, including its own
bundled Python runtime. Copy that whole folder to another Windows machine
(no install step) and double-click the `.exe`; confirmed working by
launching it with Python removed entirely from `PATH`.

**Known risk — Smart App Control / WDAC:** this `.exe` is unsigned and has
no reputation with Windows. On a machine with Smart App Control (or a
similar Windows Defender Application Control policy) in enforcement mode,
Windows can block it outright with "An application control policy has
blocked this file" — reproduced on the dev machine while building this.
This isn't a bug in the build; it's inherent to shipping an unsigned
executable. If you hit this on the target machine, the real fix is
code-signing the `.exe` (requires a paid code-signing certificate), which
is tracked as an open decision in architecture.md rather than done here.
Many Windows installs won't have this policy in enforcement mode — test on
the actual target machine before assuming it's blocked.

To rebuild from scratch (e.g. after dependency changes), delete `build/`
and `dist/` first; both are gitignored, disposable build output.

## What this slice does

- Read-only scan of a source folder for JPEG/PNG/TIFF/BMP/WEBP files
  (RAW/HEIC are a deliberately deferred decision — see architecture.md Open
  Decisions). Does not follow symlinks, file or directory.
- Reads EXIF capture date when present; otherwise falls back to the
  filesystem modified time and says so in the UI rather than hiding it.
- One editable organization rule: a destination pattern using placeholders
  `{year}` `{yy}` `{month}` `{day}` `{hour}` `{minute}` `{second}` `{name}`
  `{ext}` `{seq}`, defaulting to
  `{year}/{month}/{year}-{month}-{day}_{name}{ext}`. Edit the pattern field
  before scanning (hover it, or its label, for a full legend); an empty or
  invalid pattern is rejected with a clear message before anything runs.
  - `{yy}` is a 2-digit year (`23` instead of `2023`).
  - `{hour}`/`{minute}`/`{second}` are 2-digit, 24-hour capture time.
  - `{seq}` is a 4-digit number that resets each capture date, for
    numbering same-day bursts (e.g. `{year}/{month}/{seq}_{name}{ext}` →
    `0001_img1.jpg`, `0002_img2.jpg`, ...).
  - A pattern needs `{name}`, `{seq}`, or all of `{hour}`+`{minute}`+`{second}`
    — otherwise it's rejected as not distinguishing files from each other.
- Review table with per-row include/exclude, rationale, and warnings.
  A pre-existing file already at the destination is flagged as blocking
  and cannot be applied until resolved or excluded. Two files *within the
  same scan* that would land on the same destination (most often same-second
  photos under a time-only pattern) are instead automatically numbered
  (`_2`, `_3`, ...) rather than blocked — the renumbering shows up in that
  row's warnings, so it's automatic but never silent.
- Every review-table column is resizable by dragging its header border, and
  hovering any cell shows its full text in a tooltip even when the column
  is too narrow to display it all.
- Nothing is moved until you click Approve & Apply, and only the rows you
  approved are attempted. Each file is revalidated against its scan-time
  size/modified-time immediately before moving, so a file changed after the
  scan is skipped, not silently moved or overwritten. One file's failure
  does not stop the rest of the batch.

## What this slice does not do yet

These are in requirements.md/architecture.md's MVP scope but intentionally
out of this first build:

- Image preview/thumbnails in the review table.
- "Remove" (quarantine) actions — only rename/move is implemented.
- SQLite persistence: settings, scan cache, operation journal. (This also
  means resized column widths and the pattern field reset on restart —
  there's nowhere to save them yet.)
- Undo and operation history.
- Interrupted-run recovery.
- Background scanning (scan currently runs on the UI thread).
- Multiple named/saved rule presets (only one editable pattern at a time).

## Open product/architecture decisions

Tracked in one place: architecture.md → **Open Decisions**.
