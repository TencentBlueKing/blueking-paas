"""Running ``git`` as a controlled subprocess: no prompts, no ambient config, no leaked token.

Three decisions here are worth more than the code that implements them.

**The token never reaches the command line.** ``git -c http.extraHeader=...`` is the usual way to
authenticate a one-off command, and it puts the credential in ``argv`` -- readable through
``/proc`` by anything running as the same user, which in this container includes every command
the model runs through its Shell capability. Stripping the agent's environment for those
subprocesses (see :mod:`app_spark_agent.agent`) would then be undone by ``ps``. So the header
travels as ``GIT_CONFIG_KEY_n`` / ``GIT_CONFIG_VALUE_n`` instead, which git reads from its own
environment and which no other process inherits.

**The header is scoped to the one remote.** ``http.<url>.extraHeader`` applies only to requests
whose URL starts with ``<url>`` at a path boundary, so a redirect elsewhere -- or a second remote
someone adds to the repository later -- does not receive the Authorization header.

**Ambient configuration is switched off.** ``/etc/gitconfig`` and ``~/.gitconfig`` are ignored, as
is any inherited credential helper. A helper would otherwise be free to write the token to disk,
and the point of every choice above is that it stays in one process's memory.

Everything here is blocking on purpose. A local commit has to survive the cancellation of the
task that asked for it (see the run barrier in :mod:`app_spark_agent.server.routes`), and a
thread running ``subprocess.run`` does exactly that where an awaited coroutine does not: callers
hand these methods to ``asyncio.to_thread`` and the work finishes even if nobody is left to read
the result.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from base64 import b64encode
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from app_spark_agent.git.errors import (
    GitAuthError,
    GitCommandError,
    GitRemoteUnavailableError,
    GitTimeoutError,
)
from app_spark_agent.masking import mask_text

logger = logging.getLogger(__name__)

# Fragments of git's own English error output that identify a credential problem. Matching prose
# is unpleasant but unavoidable: git answers "403 forbidden" and "bad token" with the same exit
# code 128 it uses for "not a repository". `LC_ALL=C` below is what keeps these stable.
_AUTH_MARKERS = (
    "authentication failed",
    "could not read username",
    "could not read password",
    "terminal prompts disabled",
    "http basic: access denied",
    "403 forbidden",
    "401 unauthorized",
    "invalid username or password",
)

# The same, for a remote that is simply not answering. Worth separating because these are the
# failures a background retry will eventually get past.
_UNAVAILABLE_MARKERS = (
    "could not resolve host",
    "failed to connect",
    "connection refused",
    "connection reset",
    "operation timed out",
    "empty reply from server",
    "gnutls_handshake() failed",
    "ssl connect error",
    "the remote end hung up unexpectedly",
)


@dataclass(frozen=True)
class GitIdentity:
    """Who commits show as. A robot, never the end user.

    Git refuses to commit without both halves, so this is not optional configuration. The
    identity is handed over as ``GIT_AUTHOR_*`` / ``GIT_COMMITTER_*`` rather than written into
    ``.git/config``, keeping the repository itself free of anything this process decided.

    :param name: ``user.name`` value.
    :param email: ``user.email`` value.
    """

    name: str
    email: str


@dataclass(frozen=True)
class RemoteConfig:
    """The single remote this workspace may talk to, and the credential for it.

    :param url: HTTP(S) clone URL, without credentials in it. It is written to ``.git/config``
        as ``origin`` and is therefore readable by anyone who can read the workspace.
    :param branch: The one working branch. Neither pushes nor restores name another.
    :param username: Basic-auth username; for Forgejo this is the service account.
    :param token: Repository-scoped token, used as the Basic-auth password. Kept out of
        ``repr`` so an exception rendering a config cannot spill it into a log.
    """

    url: str
    branch: str
    username: str
    token: str = field(repr=False)

    def authorization_header(self) -> str:
        """Return the ``Authorization`` header value git should send to :attr:`url`."""
        encoded = b64encode(f"{self.username}:{self.token}".encode()).decode()
        return f"Basic {encoded}"


@dataclass(frozen=True)
class GitResult:
    """One finished ``git`` invocation.

    :param args: Argument vector, without the binary. Safe to log: credentials are never in it.
    :param returncode: Exit status.
    :param stdout: Decoded standard output.
    :param stderr: Decoded standard error, already masked.
    """

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        """Whether git reported success."""
        return self.returncode == 0

    @property
    def message(self) -> str:
        """The most useful line git produced, for an exception or a log entry."""
        lines = (self.stderr.strip() or self.stdout.strip()).splitlines()
        return lines[-1] if lines else ""


class GitRunner:
    """Invoke ``git`` against one workspace with a fixed, non-interactive configuration.

    Example::

        runner = GitRunner(
            workspace=Path("/data/workspace"),
            identity=GitIdentity(name="App-Spark", email="app-spark@localhost.invalid"),
            remote=RemoteConfig(url=..., branch="main", username="app-spark-bot", token=...),
        )
        head = runner.run("rev-parse", "HEAD").stdout.strip()

    :param workspace: Directory git runs in. Need not be a repository yet.
    :param identity: Author and committer for every commit this runner makes.
    :param remote: The remote and its credential, or ``None`` for a purely local repository
        (which is what the unit tests and an unconfigured Runtime use).
    :param timeout_seconds: Per-invocation limit. A command that outlives it is killed.
    :param git_binary: Path to ``git``; resolved from ``PATH`` when omitted.
    """

    def __init__(
        self,
        *,
        workspace: Path,
        identity: GitIdentity,
        remote: RemoteConfig | None = None,
        timeout_seconds: float = 120.0,
        git_binary: str | None = None,
    ) -> None:
        self.workspace = workspace
        self.identity = identity
        self.remote = remote
        self.timeout_seconds = timeout_seconds
        self._git_binary = git_binary

    @property
    def git_binary(self) -> str:
        """Return the ``git`` executable, failing with a setup-shaped message when absent.

        :raises GitCommandError: If no ``git`` is installed.
        """
        if self._git_binary is not None:
            return self._git_binary
        resolved = shutil.which("git")
        if resolved is None:
            raise GitCommandError("`git` is not installed in this image, so nothing can be persisted")
        self._git_binary = resolved
        return resolved

    def run(
        self,
        *args: str,
        cwd: Path | None = None,
        check: bool = True,
        timeout_seconds: float | None = None,
    ) -> GitResult:
        """Run one git command to completion.

        :param args: Arguments after the binary, e.g. ``("status", "--porcelain")``.
        :param cwd: Directory to run in; defaults to the workspace.
        :param check: Raise on a non-zero exit. ``False`` when the exit status is the answer,
            as it is for ``diff --quiet``.
        :param timeout_seconds: Override the runner's timeout for a command known to be slower.
        :return: The finished invocation.
        :raises GitTimeoutError: The command outlived its timeout and was killed.
        :raises GitAuthError: The remote refused, or asked for, credentials.
        :raises GitRemoteUnavailableError: The remote could not be reached.
        :raises GitCommandError: Any other non-zero exit, when ``check``.
        """
        limit = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        try:
            # No shell anywhere in this call: the binary is resolved, and the arguments reach
            # execve as a vector, so a path or a branch name cannot become a command.
            completed = subprocess.run(
                [self.git_binary, *args],
                cwd=cwd or self.workspace,
                env=self.build_env(),
                capture_output=True,
                timeout=limit,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            # `subprocess.run` has already killed the child and reaped it by the time it raises.
            raise GitTimeoutError(
                f"git {args[0] if args else ''} did not finish within {limit:g}s",
                args_=args,
                stderr=_decode(exc.stderr),
            ) from exc
        except OSError as exc:
            raise GitCommandError(f"could not start git: {exc}", args_=args) from exc

        result = GitResult(
            args=tuple(args),
            returncode=completed.returncode,
            stdout=_decode(completed.stdout),
            stderr=_decode(completed.stderr),
        )
        if result.ok or not check:
            return result
        raise classify_failure(result)

    def build_env(self) -> dict[str, str]:
        """Return the environment every invocation gets.

        Public because it is the security-relevant half of this class: a test asserting that no
        credential reaches ``argv`` has to be able to see where it does go instead.
        """
        env = {
            key: value
            for key, value in os.environ.items()
            # Dropped rather than overwritten: the count below has to describe *our* pairs, and
            # a stale higher-numbered key inherited from a parent would be read as one of them.
            if not key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))
        }
        env.update(
            {
                # No prompting, ever: a Runtime has no terminal, and a git that blocks waiting
                # for one would hang the run barrier until the command timed out.
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                # Error text is classified by matching English fragments below.
                "LC_ALL": "C",
                "GIT_AUTHOR_NAME": self.identity.name,
                "GIT_AUTHOR_EMAIL": self.identity.email,
                "GIT_COMMITTER_NAME": self.identity.name,
                "GIT_COMMITTER_EMAIL": self.identity.email,
            }
        )
        pairs = list(self._config_pairs())
        for index, (key, value) in enumerate(pairs):
            env[f"GIT_CONFIG_KEY_{index}"] = key
            env[f"GIT_CONFIG_VALUE_{index}"] = value
        env["GIT_CONFIG_COUNT"] = str(len(pairs))
        return env

    def _config_pairs(self) -> Iterable[tuple[str, str]]:
        """Yield the config this process imposes, as ``(key, value)``."""
        # An inherited helper is both a correctness and a secrecy problem: it could answer with
        # someone else's credential, and it is free to write ours to disk.
        yield "credential.helper", ""
        yield "commit.gpgsign", "false"
        # The workspace may be owned by a different uid than this process inside the sandbox;
        # without this git refuses to touch it at all.
        yield "safe.directory", str(self.workspace)
        # Line endings must round-trip byte-for-byte, or a restore would differ from what was
        # committed on a machine with a different default.
        yield "core.autocrlf", "false"
        # Packing is not this component's job. Left on, git would occasionally decide to repack
        # in the middle of the end-of-run barrier, turning a fast local commit into a slow one.
        yield "gc.auto", "0"
        yield "advice.detachedHead", "false"
        if self.remote is not None:
            yield f"http.{self.remote.url}.extraHeader", f"Authorization: {self.remote.authorization_header()}"


def classify_failure(result: GitResult) -> GitCommandError:
    """Turn a failed invocation into the most specific error type that fits.

    :param result: A non-zero invocation.
    :return: The exception the caller should raise.
    """
    haystack = f"{result.stderr}\n{result.stdout}".lower()
    summary = result.message or f"git {' '.join(result.args)} exited {result.returncode}"
    if any(marker in haystack for marker in _AUTH_MARKERS):
        return GitAuthError(
            f"the Git remote rejected this Runtime's credentials: {summary}",
            args_=result.args,
            returncode=result.returncode,
            stderr=result.stderr,
        )
    if any(marker in haystack for marker in _UNAVAILABLE_MARKERS):
        return GitRemoteUnavailableError(
            f"the Git remote is unreachable: {summary}",
            args_=result.args,
            returncode=result.returncode,
            stderr=result.stderr,
        )
    return GitCommandError(
        f"git {' '.join(result.args)} failed: {summary}",
        args_=result.args,
        returncode=result.returncode,
        stderr=result.stderr,
    )


def _decode(raw: bytes | str | None) -> str:
    """Decode git's output, masking any configured credential that reached it."""
    if raw is None:
        return ""
    text = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
    return mask_text(text)
