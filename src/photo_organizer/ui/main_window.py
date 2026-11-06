"""Minimal review UI: scan -> table of suggestions -> approve -> apply.

This is the thin-slice UI. It intentionally does not yet implement image
preview, undo, or operation history (requirements.md FR-5/FR-10 scope that
in full; those are deferred here, see README.md "What this build does not
do yet").

Scanning runs synchronously on the UI thread for now. architecture.md flags
background worker strategy as an open decision; for a first slice this is a
known, accepted limitation rather than a silent gap.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from photo_organizer.app.executor import execute_plan
from photo_organizer.app.suggestion_engine import build_suggestions
from photo_organizer.domain.models import ActionState, Suggestion
from photo_organizer.rules.naming import (
    DEFAULT_PATTERN,
    PLACEHOLDER_LEGEND,
    DateFolderRule,
    InvalidPatternError,
    validate_pattern,
)
from photo_organizer.scanning.scanner import scan_folder

_COL_INCLUDE = 0
_COL_SOURCE = 1
_COL_DESTINATION = 2
_COL_REASON = 3
_COL_WARNINGS = 4
_COLUMN_HEADERS = ("Include", "Current Path", "Proposed Path", "Reason", "Warnings")


def _pattern_legend_html() -> str:
    """US-16: a hover legend for the pattern field, built from
    rules.naming.PLACEHOLDER_LEGEND so the UI and the validator can never
    list different placeholders."""
    rows = "".join(f"<tr><td><code>{token}</code>&nbsp;&nbsp;</td><td>{desc}</td></tr>" for token, desc in PLACEHOLDER_LEGEND)
    return (
        "<b>Pattern placeholders</b>"
        f"<table>{rows}</table>"
        "<br>Must include <code>{name}</code>, <code>{seq}</code>, or the full "
        "<code>{hour}{minute}{second}</code>.<br>"
        "Two files that would otherwise land on the same path (e.g. same-second "
        "photos with only time-of-day) are automatically numbered, not overwritten.<br><br>"
        "<b>Example:</b> <code>{year}/{month}/{hour}-{minute}-{second}_{name}{ext}</code>"
    )


def _cell(text: str) -> QTableWidgetItem:
    """A table cell that shows its full text in a tooltip on hover (US-12),
    regardless of whether the column is currently wide enough to show it."""
    item = QTableWidgetItem(text)
    item.setToolTip(text)
    return item


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Photo Organizer (preview build)")
        self.resize(1100, 600)

        self._source_folder: Path | None = None
        self._destination_folder: Path | None = None
        self._suggestions: list[Suggestion] = []

        self._build_ui()
        self._refresh_action_state()

    # ----- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        folder_row = QHBoxLayout()
        self._source_label = QLabel("Source folder: (none selected)")
        choose_source_btn = QPushButton("Choose source folder...")
        choose_source_btn.clicked.connect(self._choose_source_folder)
        self._destination_label = QLabel("Destination folder: (none selected)")
        choose_destination_btn = QPushButton("Choose destination folder...")
        choose_destination_btn.clicked.connect(self._choose_destination_folder)
        folder_row.addWidget(self._source_label)
        folder_row.addWidget(choose_source_btn)
        folder_row.addSpacing(24)
        folder_row.addWidget(self._destination_label)
        folder_row.addWidget(choose_destination_btn)
        folder_row.addStretch()
        layout.addLayout(folder_row)

        pattern_row = QHBoxLayout()
        pattern_label = QLabel("Folder/filename pattern (hover for legend):")
        pattern_label.setToolTip(_pattern_legend_html())
        pattern_row.addWidget(pattern_label)
        self._pattern_input = QLineEdit(DEFAULT_PATTERN)
        self._pattern_input.setToolTip(_pattern_legend_html())
        pattern_row.addWidget(self._pattern_input)
        layout.addLayout(pattern_row)

        action_row = QHBoxLayout()
        self._scan_btn = QPushButton("Scan")
        self._scan_btn.clicked.connect(self._run_scan)
        self._apply_btn = QPushButton("Approve selected && Apply")
        self._apply_btn.clicked.connect(self._run_apply)
        action_row.addWidget(self._scan_btn)
        action_row.addWidget(self._apply_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        self._status_label = QLabel("Select a source folder and a destination folder, then scan.")
        layout.addWidget(self._status_label)

        self._table = QTableWidget(0, len(_COLUMN_HEADERS))
        self._table.setHorizontalHeaderLabels(_COLUMN_HEADERS)
        # US-13: every column is user-resizable by dragging its header
        # border (Interactive, rather than Stretch/Fixed, is what allows
        # that). Initial widths below are just sensible starting points.
        header = self._table.horizontalHeader()
        for col in range(len(_COLUMN_HEADERS)):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        self._table.setColumnWidth(_COL_INCLUDE, 60)
        self._table.setColumnWidth(_COL_SOURCE, 320)
        self._table.setColumnWidth(_COL_DESTINATION, 320)
        self._table.setColumnWidth(_COL_REASON, 220)
        self._table.setColumnWidth(_COL_WARNINGS, 220)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self._table)

        self.setCentralWidget(central)

    # ----- Folder selection --------------------------------------------------

    def _choose_source_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Choose source folder")
        if chosen:
            self._source_folder = Path(chosen)
            self._source_label.setText(f"Source folder: {chosen}")
            self._refresh_action_state()

    def _choose_destination_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Choose destination folder")
        if chosen:
            self._destination_folder = Path(chosen)
            self._destination_label.setText(f"Destination folder: {chosen}")
            self._refresh_action_state()

    # ----- Scan --------------------------------------------------------------

    def _run_scan(self) -> None:
        if self._source_folder is None or self._destination_folder is None:
            return

        pattern = self._pattern_input.text()
        try:
            validate_pattern(pattern)
        except InvalidPatternError as exc:
            QMessageBox.warning(self, "Invalid pattern", str(exc))
            return

        self._status_label.setText("Scanning (read-only; no files are changed)...")
        records, skipped_other = scan_folder(self._source_folder)

        rule = DateFolderRule(destination_root=self._destination_folder, pattern=pattern)
        self._suggestions = build_suggestions(records, rule)
        self._populate_table()

        blocking = sum(1 for s in self._suggestions if s.has_blocking_warning)
        self._status_label.setText(
            f"Scanned {len(records)} supported file(s), skipped {skipped_other} unsupported file(s). "
            f"{blocking} row(s) have a blocking warning and cannot be applied until resolved or excluded."
        )
        self._refresh_action_state()

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._suggestions))
        for row, suggestion in enumerate(self._suggestions):
            include_item = QTableWidgetItem()
            include_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            include_item.setCheckState(Qt.Checked if suggestion.included else Qt.Unchecked)
            self._table.setItem(row, _COL_INCLUDE, include_item)

            source_text = str(suggestion.source)
            destination_text = str(suggestion.destination)
            warnings_text = "; ".join(suggestion.warnings)

            # US-12: full text on hover, independent of how narrow the
            # column currently is.
            self._table.setItem(row, _COL_SOURCE, _cell(source_text))
            self._table.setItem(row, _COL_DESTINATION, _cell(destination_text))
            self._table.setItem(row, _COL_REASON, _cell(suggestion.rationale))
            self._table.setItem(row, _COL_WARNINGS, _cell(warnings_text))

            if suggestion.has_blocking_warning:
                for col in range(len(_COLUMN_HEADERS)):
                    item = self._table.item(row, col)
                    if item is not None:
                        item.setBackground(Qt.red)

    def _collect_included_from_table(self) -> list[Suggestion]:
        for row, suggestion in enumerate(self._suggestions):
            include_item = self._table.item(row, _COL_INCLUDE)
            suggestion.included = include_item is not None and include_item.checkState() == Qt.Checked
        return self._suggestions

    # ----- Apply ---------------------------------------------------------------

    def _run_apply(self) -> None:
        suggestions = self._collect_included_from_table()
        approved = [s for s in suggestions if s.included]

        blocked = [s for s in approved if s.has_blocking_warning]
        if blocked:
            QMessageBox.warning(
                self,
                "Cannot apply",
                f"{len(blocked)} selected row(s) still have a blocking warning "
                "(collision or read error). Exclude them or resolve the conflict first.",
            )
            return

        if not approved:
            QMessageBox.information(self, "Nothing to apply", "No rows are selected.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm",
            f"Move {len(approved)} file(s) as shown? This is the exact set of actions that will run.",
        )
        if confirm != QMessageBox.Yes:
            return

        results = execute_plan(approved)
        succeeded = sum(1 for r in results if r.state == ActionState.SUCCEEDED)
        skipped = sum(1 for r in results if r.state == ActionState.SKIPPED)
        failed = sum(1 for r in results if r.state == ActionState.FAILED)

        for result in results:
            row = self._suggestions.index(result.suggestion)
            self._table.setItem(row, _COL_WARNINGS, _cell(f"{result.state.value}: {result.message}"))

        self._status_label.setText(
            f"Apply finished: {succeeded} succeeded, {skipped} skipped, {failed} failed."
        )

    # ----- Misc ------------------------------------------------------------

    def _refresh_action_state(self) -> None:
        ready_to_scan = self._source_folder is not None and self._destination_folder is not None
        self._scan_btn.setEnabled(ready_to_scan)
        self._apply_btn.setEnabled(bool(self._suggestions))
