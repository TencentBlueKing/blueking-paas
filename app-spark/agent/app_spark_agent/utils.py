"""Shared helpers that depend on nothing else in the package.

Crash-safe file writes, which both state modules need and neither owns, plus a small process
helper whose failure mode is spelled out in its name. The file helpers are blocking, so async
callers must hand them to ``asyncio.to_thread``.
"""

import contextlib
import os
import secrets
import signal
from pathlib import Path


def killpg_ignore_absent(pgid: int, sig: signal.Signals) -> None:
    """Send sig to the process group pgid. A group that has already exited is not an error."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pgid, sig)


def write_atomic(path: Path, data: bytes) -> None:
    """Replace ``path`` with ``data`` in a single step.

    A reader either sees the previous file or the new one, never a half-written mix: the
    content is staged in a sibling temporary file, fsynced, and moved into place with
    ``os.replace``, which is atomic within one filesystem.

    Every call stages in a file of its own, so concurrent writers of the same path cannot
    delete or replace each other's staging file; the last replace wins.
    """
    temporary_path = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        # "x" refuses an existing file rather than writing into someone else's staging file. Unlike
        # tempfile.mkstemp it keeps the umask-derived mode, which the replaced file then carries.
        with temporary_path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        # A no-op after a successful replace; it is what removes this call's staging file when
        # the write or the replace failed.
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
