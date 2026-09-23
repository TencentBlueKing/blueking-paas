"""What of a workspace is persisted, and what is refused.

This is deliberately a settled policy rather than an open question, because the end-of-run
barrier's latency budget is derived from it: "commit whatever is there" is not a bounded amount
of work when a dependency directory can be hundreds of megabytes.

**Included.** Source, configuration, static assets, lock files -- and dotfiles among them. Hidden
files are ordinary project files (``.gitignore``, ``.python-version``, ``.env``), the repository
is private and per-Project, and a restore that quietly dropped the app's configuration would be
a worse failure than storing it. The one exception git makes for us is ``.git`` itself.

**Excluded by default.** Directories that are derived from files we do keep, listed in
:func:`get_default_excludes`. Losing them costs a reinstall; keeping them costs the whole latency and
size budget.

**Binary files** are committed as-is. Git stores them whole rather than as deltas, which is what
:class:`WorkspacePolicy` bounds instead of forbidding.

**Symbolic links** are committed as links -- git stores the link text, never the target's
content. A restore therefore recreates a link, and a link that pointed outside the workspace
comes back pointing at whatever now lives at that path. That is a property to know about, not one
to work around: rejecting symlinks would break virtualenvs and ``node_modules`` layouts that the
default excludes already keep out anyway.

**Ignored files** are honoured, from both sides: the user's own ``.gitignore`` files, which are
committed like any other source, and this policy's defaults. The defaults go to
``.git/info/exclude`` rather than to a ``.gitignore`` the platform writes into the workspace --
that file belongs to the project, and an imported workspace that already has one must not have it
overwritten. ``info/exclude`` is inside ``.git``, is never committed, and stacks with whatever the
project says for itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from app_spark_agent.git.errors import GitPolicyError
from app_spark_agent.git.ignores import load_default_excludes


@cache
def get_default_excludes() -> tuple[str, ...]:
    """Return the platform ignore list, reading vendored templates on first call.

    Importing this module does not touch ``git/assets``, so
    ``make update-gitignore-assets`` can run against an empty directory. The
    result is cached: every :class:`WorkspacePolicy` shares one tuple.
    """
    return load_default_excludes()


# Header written above the generated exclude list, so a developer who opens the file knows why it
# is there and that editing it is pointless.
_EXCLUDE_HEADER = """\
# Written by App-Spark. Regenerated on every Runtime start; edits are lost.
# Project-owned rules belong in .gitignore, which is committed and takes precedence
# through the usual gitignore ordering.
"""

DEFAULT_MAX_FILE_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 200 * 1024 * 1024

# How many offending paths an error names. Enough to see the pattern, not enough to bury it.
_REPORTED_PATHS = 10


@dataclass(frozen=True)
class WorkspaceFile:
    """One candidate for the next commit.

    :param path: Workspace-relative path, as git reports it.
    :param size: Size in bytes; ``0`` for a path that no longer exists on disk (a deletion,
        which costs nothing to record).
    """

    path: str
    size: int


@dataclass(frozen=True)
class WorkspacePolicy:
    """Which files are committed, and the hard ceilings on how much.

    The ceilings are refusals, not warnings. A workspace that grows past them stops being
    persisted, loudly, naming what pushed it over -- because the alternative is an end-of-run
    barrier that quietly takes minutes, or a push that fills the Git host.

    :param max_file_bytes: Largest single file that may be committed.
    :param max_total_bytes: Largest total across everything that would be committed.
    :param excludes: ``.gitignore`` patterns applied on top of the project's own rules.
    """

    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    excludes: tuple[str, ...] = field(default_factory=get_default_excludes)

    def exclude_document(self) -> str:
        """Return the full text of the ``.git/info/exclude`` file this policy implies."""
        return _EXCLUDE_HEADER + "\n".join(self.excludes) + "\n"

    def check(self, files: Sequence[WorkspaceFile]) -> None:
        """Refuse a commit whose content is outside the ceilings.

        Checked before anything is staged, so a refusal leaves the index exactly as it was and a
        caller can report the problem without first having to undo half an operation.

        :param files: Everything that would be committed: tracked plus untracked-and-not-ignored.
        :raises GitPolicyError: A single file or the total is over the ceiling.
        """
        oversized = sorted(
            (item for item in files if item.size > self.max_file_bytes),
            key=lambda item: item.size,
            reverse=True,
        )
        if oversized:
            raise GitPolicyError(
                f"{len(oversized)} file(s) exceed the {_human(self.max_file_bytes)} per-file limit "
                f"and cannot be saved: {_describe(oversized)}. Delete them or add them to .gitignore.",
                paths=[item.path for item in oversized],
            )

        total = sum(item.size for item in files)
        if total > self.max_total_bytes:
            largest = sorted(files, key=lambda item: item.size, reverse=True)
            raise GitPolicyError(
                f"the workspace holds {_human(total)} of committable files, over the "
                f"{_human(self.max_total_bytes)} limit. Largest: {_describe(largest)}. "
                "Add rebuildable directories to .gitignore.",
                paths=[item.path for item in largest[:_REPORTED_PATHS]],
            )


def measure(root: Path, paths: Sequence[str]) -> list[WorkspaceFile]:
    """Size each of ``paths`` under ``root``.

    Uses ``lstat`` so a symlink is measured as the link it is rather than as whatever it points
    at -- which is also how git will store it.

    :param root: Workspace root the paths are relative to.
    :param paths: Workspace-relative paths, as git reported them.
    :return: One entry per path, missing files measured as zero.
    """
    measured: list[WorkspaceFile] = []
    for path in paths:
        try:
            size = (root / path).lstat().st_size
        except OSError:
            # Reported by git but gone from disk: a deletion, or a file removed between the
            # listing and now. Either way it adds nothing to the commit.
            size = 0
        measured.append(WorkspaceFile(path=path, size=size))
    return measured


def _describe(files: Sequence[WorkspaceFile]) -> str:
    """Render the worst offenders as ``path (size)``, truncated."""
    shown = ", ".join(f"{item.path} ({_human(item.size)})" for item in files[:_REPORTED_PATHS])
    remaining = len(files) - _REPORTED_PATHS
    return f"{shown}, and {remaining} more" if remaining > 0 else shown


def _human(size: int) -> str:
    """Render a byte count the way an error message should read."""
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    raise AssertionError("unreachable")  # pragma: no cover
