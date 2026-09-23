"""Failure modes of the Git workspace, split by what a caller can do about them.

Git reports almost everything as exit code 128 plus English prose, so a caller that only sees
``CalledProcessError`` has to re-parse that prose to decide anything. The distinctions below are
the ones later stages actually branch on: a diverged push has to surface as a conflict rather
than as a retry, an unreachable remote is worth retrying forever, and a bad token is not.
"""

from __future__ import annotations

from collections.abc import Sequence


class GitError(Exception):
    """Base class for everything this package raises."""


class GitNotConfiguredError(GitError):
    """Git persistence was used without a remote or a token configured."""


class GitCommandError(GitError):
    """A ``git`` invocation exited non-zero.

    :param message: What was being attempted, in the caller's terms.
    :param args_: The argument vector, credentials never among them.
    :param returncode: Exit status.
    :param stderr: Masked standard error, kept for the log line that has to explain this.
    """

    def __init__(
        self,
        message: str,
        *,
        args_: Sequence[str] = (),
        returncode: int = 0,
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.args_ = tuple(args_)
        self.returncode = returncode
        self.stderr = stderr


class GitTimeoutError(GitCommandError):
    """A ``git`` invocation outlived its timeout and was killed.

    Distinct from a plain failure because the command may well have half-finished: a killed
    ``push`` can still have transferred its objects, so the remote is the only authority on
    whether it landed.
    """


class GitAuthError(GitCommandError):
    """The remote refused the credentials, or asked for credentials this process would not give.

    Not retryable on its own: the token is long-lived, so the same request will keep failing
    until the control plane re-issues one.
    """


class GitRemoteUnavailableError(GitCommandError):
    """The remote could not be reached. Retrying later is the correct response."""


class GitDivergedError(GitCommandError):
    """The remote branch holds commits this workspace does not, so a plain push was rejected.

    Never resolved by forcing. On the working branch this means another writer got there first,
    and the server-side ban on non-fast-forward pushes is the whole reason a stale Runtime
    cannot overwrite live work.
    """


class GitWorkspaceConflictError(GitError):
    """An existing workspace and an existing remote branch cannot be joined without losing one.

    Raised instead of guessing: overwriting the workspace destroys work that was never pushed,
    and committing the workspace on top of the remote tip silently deletes every remote file the
    workspace happens not to have.
    """


class GitPolicyError(GitError):
    """The workspace holds content the file policy refuses to commit.

    :param message: Human-readable summary, already naming the worst offenders.
    :param paths: Offending paths, largest first, so a caller can report them without
        re-deriving them from the message text.
    """

    def __init__(self, message: str, *, paths: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.paths = tuple(paths)
