"""Photo Organizer: local-first photo rename/move assistant.

See architecture.md for the full design. This package currently implements
the thin vertical slice described there: scan -> suggest (one date-based
rule) -> review -> approve -> execute, with no overwrite and per-file error
isolation. Undo/history/journal persistence are not yet implemented.
"""
