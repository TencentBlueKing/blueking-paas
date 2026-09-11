"""The workspace as a Git working tree: attach it to a remote, commit it, push it, restore it.

Nothing here knows about runs, conversations, or HTTP. That separation is the point of the stage
this module lands in: the end-of-run barrier is a bad place to discover that Git behaves
differently than assumed, so every Git behaviour worth relying on is settled and tested here
first, against real ``git`` processes and a real remote.

Two invariants hold throughout and are not configurable:

- **One remote, one branch.** Every push targets ``refs/heads/<branch>`` on ``origin``. Nothing
  in this module names another ref, so "which branch did that turn land on" has one answer.
- **No force, ever.** A rejected push is reported as :class:`GitDivergedError` and left for a
  human or a higher layer to resolve. The remote refuses non-fast-forward pushes for the same
  reason, and that refusal is what stops a stale Runtime from overwriting live work -- a force
  flag here would be a way around the only defence there is.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app_spark_agent import settings
from app_spark_agent.git.errors import (
    GitCommandError,
    GitDivergedError,
    GitNotConfiguredError,
    GitWorkspaceConflictError,
)
from app_spark_agent.git.policy import WorkspaceFile, WorkspacePolicy, measure
from app_spark_agent.git.runner import GitIdentity, GitRunner, RemoteConfig, classify_failure

logger = logging.getLogger(__name__)

# What `ensure_ready` did, for the caller's log line.
ReadyAction = Literal["initialised", "cloned", "reused"]

# Push rejections that mean "the remote moved on", as opposed to a transport or auth failure.
_DIVERGED_MARKERS = (
    "non-fast-forward",
    "fetch first",
    "cannot lock ref",
    "stale info",
)


@dataclass(frozen=True)
class StatusEntry:
    """One path git reports as changed.

    :param path: Workspace-relative path; the destination path for a rename.
    :param index_status: Git's index (staged) status letter, a space when unstaged.
    :param worktree_status: Git's working-tree status letter, a space when clean.
    :param renamed_from: The source path when git detected a rename, otherwise ``None``.
    """

    path: str
    index_status: str
    worktree_status: str
    renamed_from: str | None = None

    @property
    def untracked(self) -> bool:
        """Whether git has never seen this path before."""
        return self.index_status == "?"


@dataclass(frozen=True)
class WorkspaceStatus:
    """Everything git considers changed right now.

    :param entries: One per changed path, in git's own order.
    """

    entries: tuple[StatusEntry, ...]

    @property
    def dirty(self) -> bool:
        """Whether there is anything at all to commit."""
        return bool(self.entries)

    @property
    def paths(self) -> tuple[str, ...]:
        """The changed paths, for a log line or an error."""
        return tuple(entry.path for entry in self.entries)


class GitWorkspace:
    """One workspace directory, managed as a Git working tree.

    Every method is blocking; see :mod:`app_spark_agent.git.runner` for why that is deliberate
    rather than an oversight. Async callers use ``asyncio.to_thread``.

    Example::

        workspace = GitWorkspace(path=Path("/data/workspace"), runner=runner)
        workspace.ensure_ready()
        if (sha := workspace.commit("turn 1")) is not None:
            workspace.push()

    :param path: The workspace directory. Must already exist.
    :param runner: Configured git process runner; carries the remote and the commit identity.
    :param policy: File policy; the default ceilings apply when omitted.
    """

    def __init__(
        self,
        *,
        path: Path,
        runner: GitRunner,
        policy: WorkspacePolicy | None = None,
    ) -> None:
        self.path = path
        self.runner = runner
        self.policy = policy or WorkspacePolicy()

    @classmethod
    def from_settings(cls, path: Path) -> GitWorkspace:
        """Build the workspace the environment describes.

        :param path: The workspace directory.
        :return: A workspace pointed at the configured remote.
        :raises GitNotConfiguredError: If Git persistence is not configured for this Runtime.
        """
        if not settings.is_git_configured():
            raise GitNotConfiguredError(
                f"{settings.ENV_PREFIX}GIT_REMOTE_URL and {settings.ENV_PREFIX}GIT_TOKEN are "
                "both required before a workspace can be persisted"
            )
        runner = GitRunner(
            workspace=path,
            identity=GitIdentity(name=settings.GIT_AUTHOR_NAME, email=settings.GIT_AUTHOR_EMAIL),
            remote=RemoteConfig(
                url=settings.GIT_REMOTE_URL,
                branch=settings.GIT_BRANCH,
                username=settings.GIT_USERNAME,
                token=settings.GIT_TOKEN,
            ),
            timeout_seconds=settings.GIT_COMMAND_TIMEOUT_SECONDS,
        )
        return cls(
            path=path,
            runner=runner,
            policy=WorkspacePolicy(
                max_file_bytes=settings.GIT_MAX_FILE_BYTES,
                max_total_bytes=settings.GIT_MAX_TOTAL_BYTES,
            ),
        )

    @property
    def branch(self) -> str:
        """The single working branch this workspace pushes to."""
        return self.runner.remote.branch if self.runner.remote else "main"

    @property
    def initialised(self) -> bool:
        """Whether the directory is already a Git repository."""
        return (self.path / ".git").exists()

    def ensure_ready(self) -> ReadyAction:
        """Make the workspace a working tree attached to the configured remote.

        Three situations, and the fourth is refused:

        - No repository and nothing on the remote: initialise an empty one. The first push
          creates the branch.
        - No repository and a remote branch with history: fetch and check it out, which is
          ``git clone`` spelled out (clone itself insists on an empty directory, and a recycled
          sandbox may hold ignored leftovers like ``.venv``).
        - A repository already here: leave the working tree exactly as it is. Deciding whether
          to move it to some other commit is a caller's judgement, not a side effect of opening.
        - Files in the workspace *and* history on the remote: refused. Either answer loses data,
          so this one is a caller's to make.

        :return: What it did, for the caller's log line.
        :raises GitWorkspaceConflictError: The workspace and the remote both hold content.
        """
        fresh = not self.initialised
        if fresh:
            self.runner.run("init", "-b", self.branch)
        # Written before anything inspects the tree, so the very first status already applies
        # the policy rather than counting a 300MB `.venv` as pending work.
        self._write_exclude()
        self._configure_remote()

        if self.runner.remote is None or self.remote_branch_head() is None:
            # Local-only, or a remote whose branch does not exist yet. Either way there is
            # nothing to take, and the first push is what creates the branch.
            return "initialised" if fresh else "reused"
        if not fresh:
            return "reused"

        self.fetch()
        occupied = self._committable_paths()
        if occupied:
            raise GitWorkspaceConflictError(
                f"{self.path} already holds {len(occupied)} file(s) and {self.branch} on the "
                f"remote already has history; joining them would lose one side. "
                f"Local files: {', '.join(occupied[:10])}"
            )
        self.runner.run("checkout", "--force", "-B", self.branch, f"origin/{self.branch}")
        return "cloned"

    def status(self) -> WorkspaceStatus:
        """Report what has changed since the last commit, ignored files excluded."""
        result = self.runner.run("status", "--porcelain=v1", "-z", "--untracked-files=normal")
        return WorkspaceStatus(entries=tuple(_parse_status(result.stdout)))

    def committable(self) -> list[WorkspaceFile]:
        """List everything that would go into a commit, with sizes.

        Tracked files plus untracked ones that no ignore rule covers -- the exact set the policy
        has an opinion about, obtained without staging anything.
        """
        return measure(self.path, self._committable_paths())

    def commit(self, message: str, *, trailers: Mapping[str, str] | None = None) -> str | None:
        """Stage every change and record one commit.

        Additions, modifications, deletions and renames are all covered by staging the whole
        tree; git works out renames itself when a diff is later read.

        :param message: Commit subject.
        :param trailers: ``Key: value`` lines appended to the message body, which is how a
            commit is tied back to the run that produced it.
        :return: The new commit's SHA, or ``None`` when there was nothing to record. An empty
            commit is not made: a turn that changed no files must not look like one that did.
        :raises GitPolicyError: The workspace holds more than the file policy allows.
        """
        self.policy.check(self.committable())
        self.runner.run("add", "--all", "--", ".")
        if not self._has_staged_changes():
            return None
        self.runner.run("commit", "--no-verify", "--quiet", "--message", _build_message(message, trailers))
        head = self.head()
        logger.info("committed %s to the workspace repository", head)
        return head

    def push(self) -> str:
        """Push the working branch to the remote.

        :return: The SHA now on the remote branch.
        :raises GitNotConfiguredError: No remote is configured.
        :raises GitDivergedError: The remote holds commits this workspace does not.
        :raises GitAuthError: The remote rejected the token.
        :raises GitRemoteUnavailableError: The remote could not be reached.
        """
        remote = self._require_remote()
        head = self.head()
        if head is None:
            raise GitCommandError("there is nothing to push: the workspace has no commits yet")
        # Fully-qualified on both sides so the push cannot be redirected by a `push.default` or
        # a branch upstream someone configured; and never `--force`.
        result = self.runner.run(
            "push",
            "--no-verify",
            "origin",
            f"refs/heads/{remote.branch}:refs/heads/{remote.branch}",
            check=False,
        )
        if not result.ok:
            if _is_diverged(result.stderr):
                raise GitDivergedError(
                    f"the remote {remote.branch} has commits this workspace does not, so the push "
                    f"was rejected; it will not be forced: {result.message}",
                    args_=result.args,
                    returncode=result.returncode,
                    stderr=result.stderr,
                )
            raise classify_failure(result)
        logger.info("pushed %s to %s", head, remote.branch)
        return head

    def tag_checkpoint(self, name: str, commit: str) -> None:
        """Pin ``commit`` under an immovable remote tag, so it can never be collected.

        A checkpoint that recorded only a SHA would rot: once the commit stops being reachable
        from any ref, the server is free to garbage-collect it, and the checkpoint silently stops
        being restorable. Branch protection does not help -- it forbids rewriting history, not
        an object becoming unreachable.

        Immovable in both directions: the tag is created without ``--force``, and pushed without
        it, so an existing tag of the same name is never repointed. Re-tagging the same commit
        under the same name is therefore a no-op rather than an error, which is what makes this
        safe to retry.

        :param name: Tag name, unique per checkpoint.
        :param commit: The commit to pin.
        :raises GitNotConfiguredError: No remote is configured.
        :raises GitCommandError: The tag exists on the remote pointing at a different commit.
        """
        remote = self._require_remote()
        existing = self.runner.run("rev-parse", "--verify", "--quiet", f"refs/tags/{name}", check=False)
        if not existing.ok:
            self.runner.run("tag", name, commit)
        result = self.runner.run(
            "push",
            "--no-verify",
            "origin",
            f"refs/tags/{name}:refs/tags/{name}",
            check=False,
        )
        if not result.ok:
            # Either somebody else already pinned this name to a different commit, or the
            # transport failed. Both need the caller to know; neither is fixed by forcing.
            raise classify_failure(result)
        logger.info("pinned checkpoint %s at %s on %s", name, commit, remote.branch)

    def is_ancestor(self, commit: str, descendant: str) -> bool:
        """Whether ``commit`` is reachable from ``descendant``.

        The question a cold start has to answer before touching anything: has the Project's
        branch simply moved on past this checkpoint, or has it gone somewhere else entirely?
        """
        return self.runner.run("merge-base", "--is-ancestor", commit, descendant, check=False).ok

    def fetch(self) -> None:
        """Bring remote-tracking refs and tags up to date.

        :raises GitNotConfiguredError: No remote is configured.
        """
        self._require_remote()
        self.runner.run("fetch", "--tags", "--prune", "origin")

    def head(self) -> str | None:
        """Return the current commit, or ``None`` on a branch with no commits yet."""
        result = self.runner.run("rev-parse", "--verify", "--quiet", "HEAD", check=False)
        return result.stdout.strip() or None

    def remote_branch_head(self) -> str | None:
        """Ask the remote what the working branch points at, without fetching.

        :return: The SHA, or ``None`` when the branch does not exist there yet.
        :raises GitAuthError: The remote rejected the token.
        :raises GitRemoteUnavailableError: The remote could not be reached.
        """
        remote = self._require_remote()
        result = self.runner.run("ls-remote", "--heads", remote.url, remote.branch)
        first = result.stdout.split()
        return first[0] if first else None

    def has_commit(self, commit: str) -> bool:
        """Whether ``commit`` is present in this repository."""
        return self.runner.run("cat-file", "-e", f"{commit}^{{commit}}", check=False).ok

    def unpushed_commits(self) -> int:
        """How many local commits the remote is not known to have.

        Answers from the last fetch rather than from the network: this is asked on paths that
        must not block, and a stale answer erring towards "there is something to push" is the
        harmless direction to be wrong in.

        With no remote-tracking branch -- a repository that has never fetched, or a remote where
        the working branch does not exist yet -- every local commit counts. Reporting nothing
        outstanding there would be the one wrong answer: that is precisely the state of a
        Runtime holding a first turn it has not managed to push.

        :return: The number of commits not yet known to be on the remote.
        """
        if self.head() is None:
            return 0
        remote_ref = f"origin/{self.branch}"
        span = (
            f"{remote_ref}..HEAD"
            if self.runner.run("rev-parse", "--verify", "--quiet", remote_ref, check=False).ok
            else "HEAD"
        )
        result = self.runner.run("rev-list", "--count", span, check=False)
        counted = result.stdout.strip()
        return int(counted) if result.ok and counted.isdigit() else 0

    def restore(self, commit: str) -> None:
        """Force the working tree to ``commit``.

        Destructive by design and by name: uncommitted changes and untracked files are
        discarded, because the only caller is a cold start whose whole job is to reproduce a
        checkpoint exactly. Ignored files are left alone -- re-downloading a ``.venv`` that is
        already on disk would be a slow way to achieve nothing.

        :param commit: The checkpoint's SHA.
        :raises GitCommandError: The commit is not on the remote either, so it cannot be reached.
        """
        if not self.has_commit(commit) and self.runner.remote is not None:
            self.fetch()
        if not self.has_commit(commit):
            raise GitCommandError(
                f"checkpoint commit {commit} is not in this repository and the remote does not "
                "have it either; the workspace cannot be restored to it"
            )
        self.runner.run("checkout", "--force", "-B", self.branch, commit)
        self.runner.run("clean", "--force", "-d")
        logger.info("restored the workspace to %s", commit)

    def _require_remote(self) -> RemoteConfig:
        """Return the configured remote, or explain that there is none."""
        if self.runner.remote is None:
            raise GitNotConfiguredError("this workspace has no Git remote configured")
        return self.runner.remote

    def _configure_remote(self) -> None:
        """Point ``origin`` at the configured URL, adding it when missing.

        The URL is written to ``.git/config`` deliberately -- and the credential is not. That is
        the whole reason the token travels as a request header instead.
        """
        if self.runner.remote is None:
            return
        url = self.runner.remote.url
        existing = self.runner.run("remote", "get-url", "origin", check=False)
        if not existing.ok:
            self.runner.run("remote", "add", "origin", url)
        elif existing.stdout.strip() != url:
            self.runner.run("remote", "set-url", "origin", url)

    def _write_exclude(self) -> None:
        """Refresh ``.git/info/exclude`` with the platform's default ignore rules."""
        info_dir = self.path / ".git" / "info"
        info_dir.mkdir(parents=True, exist_ok=True)
        (info_dir / "exclude").write_text(self.policy.exclude_document(), encoding="utf-8")

    def _committable_paths(self) -> list[str]:
        """List tracked and not-ignored-untracked paths, as git sees them."""
        result = self.runner.run("ls-files", "-z", "--cached", "--others", "--exclude-standard")
        return [path for path in result.stdout.split("\0") if path]

    def _has_staged_changes(self) -> bool:
        """Whether the index differs from HEAD, including on a branch with no commits."""
        head = self.head()
        if head is None:
            # No HEAD to diff against; anything in the index is a change.
            return bool(self.runner.run("ls-files", "-z", "--cached").stdout.strip("\0"))
        return not self.runner.run("diff", "--cached", "--quiet", check=False).ok


def _parse_status(raw: str) -> list[StatusEntry]:
    """Parse ``git status --porcelain=v1 -z`` output.

    The NUL-separated form is the only one that survives paths with spaces or newlines in them,
    at the cost of having to be parsed by hand: a rename entry is followed by a second record
    holding the original path.
    """
    fields = [field for field in raw.split("\0") if field]
    entries: list[StatusEntry] = []
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if len(record) < 4:
            continue
        index_status, worktree_status, path = record[0], record[1], record[3:]
        renamed_from = None
        if "R" in (index_status, worktree_status) and index < len(fields):
            renamed_from = fields[index]
            index += 1
        entries.append(
            StatusEntry(
                path=path,
                index_status=index_status,
                worktree_status=worktree_status,
                renamed_from=renamed_from,
            )
        )
    return entries


def _build_message(subject: str, trailers: Mapping[str, str] | None) -> str:
    """Assemble a commit message with its trailer block."""
    if not trailers:
        return subject
    lines = "\n".join(f"{key}: {value}" for key, value in trailers.items())
    return f"{subject}\n\n{lines}\n"


def _is_diverged(stderr: str) -> bool:
    """Whether a push failure means the remote branch moved on."""
    lowered = stderr.lower()
    return any(marker in lowered for marker in _DIVERGED_MARKERS)
