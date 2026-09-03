"""Shared helpers that depend on nothing else in the package.

Currently only crash-safe file writes: both state modules need them, and neither owns them.
Every function here is blocking, so async callers must hand them to ``asyncio.to_thread``.
"""

from __future__ import annotations

import os
from pathlib import Path


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
