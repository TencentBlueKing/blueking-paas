"""Shared helpers that depend on nothing else in the package.

Crash-safe file writes, which both state modules need and neither owns, plus a few small
process and file helpers whose failure modes are spelled out in their names. The file helpers
are blocking, so async callers must hand them to ``asyncio.to_thread``.
"""

import contextlib
import os
import signal
from pathlib import Path


def killpg_ignore_absent(pgid: int, sig: signal.Signals) -> None:
    """Send sig to the process group pgid. A group that has already exited is not an error."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pgid, sig)


def append_text_ignore_unwritable(path: Path, text: str) -> None:
    """Append text to path, creating it if needed; drop the text when the file cannot be written."""
    with contextlib.suppress(OSError), path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def write_atomic(path: Path, data: bytes) -> None:
    """Replace ``path`` with ``data`` in a single step.

    A reader either sees the previous file or the new one, never a half-written mix: the
    content is staged in a sibling temporary file, fsynced, and moved into place with
    ``os.replace``, which is atomic within one filesystem.
    """
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        with temporary_path.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        # A no-op after a successful replace; it is what removes the staging file when the
        # write or the replace failed.
        temporary_path.unlink(missing_ok=True)


def append_durably(path: Path, data: bytes) -> None:
    """Append ``data`` to ``path``, creating it if needed, and return only once it is on disk."""
    with path.open("ab") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def truncate_durably(path: Path, size: int) -> None:
    """Cut ``path`` down to its first ``size`` bytes and return only once that is on disk."""
    with path.open("r+b") as handle:
        handle.truncate(size)
        handle.flush()
        os.fsync(handle.fileno())
