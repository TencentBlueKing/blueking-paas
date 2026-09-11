"""Saving each turn's files: commit inside the run barrier, push behind it.

The split is the whole design, and it follows the shape :mod:`app_spark_agent.replication`
already uses for conversation state. Two facts about the barrier force it:

- The barrier's ``finally`` runs on a client disconnect just as it does on a completed turn, so
  a good share of saves happen inside a **cancelled** task, where every ``await`` may raise
  immediately.
- On SIGTERM, uvicorn's graceful shutdown deliberately cuts in-flight SSE off after one second.

A network push started in that position cannot be guaranteed to finish -- and "it finished" is
exactly the guarantee this feature exists to provide. It would also hold the stream open on a
network round trip, which the user experiences as the turn hanging.

So the barrier does the part that is local, fast and deterministic: stage the files and record a
commit. It completes even under cancellation, because it runs on a worker thread and threads do
not get cancelled. The push is a background task with its own retries, and how far behind it is
becomes something ``/health`` reports rather than something the turn waits on.

The consequence has to be said out loud rather than hidden: **when a turn's stream ends, the code
is committed locally, not saved remotely.** The two are separate states, and the Runtime reports
both.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from enum import StrEnum

from app_spark_agent import settings
from app_spark_agent.git.errors import (
    GitAuthError,
    GitDivergedError,
    GitError,
    GitPolicyError,
)
from app_spark_agent.git.workspace import GitWorkspace

logger = logging.getLogger(__name__)


# Namespaced so a checkpoint tag can never collide with a tag the project itself created, and
# so every tag this platform owns can be recognised -- and reclaimed -- by prefix alone.
CHECKPOINT_TAG_PREFIX = "app-spark/checkpoint/"


def checkpoint_tag(run_id: str) -> str:
    """Name the immovable tag that pins one turn's commit."""
    return f"{CHECKPOINT_TAG_PREFIX}{run_id}"


@dataclass(frozen=True)
class Checkpoint:
    """One restorable point: which commit, pinned under which tag, produced by which turn.

    :param run_id: The turn that produced the commit.
    :param conversation_id: The conversation that turn belonged to.
    :param commit: The commit SHA, confirmed on the remote.
    :param tag: The immovable remote tag keeping that commit reachable.
    :param context_version: The conversation version these files go with.
    """

    run_id: str
    conversation_id: str
    commit: str
    tag: str
    context_version: int


# Told about a checkpoint once its commit and tag are both on the remote. Async because the only
# real implementation is an HTTP call to the control plane.
CheckpointReporter = Callable[[Checkpoint], Awaitable[None]]


@dataclass(frozen=True)
class _Turn:
    """Which turn the commits waiting to be pushed came from, and where it left the conversation.

    The version is taken when the commit is made rather than when the push finally lands, so the
    checkpoint names the conversation as it stood at the moment those files were written. Reading
    it later would risk pairing this turn's files with a version a *subsequent* turn produced.
    """

    run_id: str
    conversation_id: str
    context_version: int


class RestoreOutcome(StrEnum):
    """What restoring a workspace to a checkpoint actually had to do."""

    # The workspace was already at the checkpoint.
    ALREADY_THERE = "already_there"
    # The working tree was moved to the checkpoint.
    RESTORED = "restored"
    # The branch has advanced past the checkpoint, and the newer work was kept.
    SUPERSEDED = "superseded"


class SaveState(StrEnum):
    """How far this Runtime's workspace has got towards being saved remotely."""

    # Nothing has been committed yet, or the last push left nothing outstanding and no commit
    # has happened since. Distinct from SAVED only in that nothing has ever been pushed.
    IDLE = "idle"
    # A local commit exists that the remote does not have.
    PENDING = "pending"
    # A push is in flight.
    PUSHING = "pushing"
    # Every local commit is on the remote.
    SAVED = "saved"
    # The last attempt failed. `detail` says why, and whether retrying can help.
    FAILED = "failed"


@dataclass(frozen=True)
class SaveStatus:
    """A snapshot of the workspace's save progress, cheap enough for a health probe.

    Held in memory and updated by the operations themselves. ``/health`` is a kube probe, so it
    must not shell out to git to answer.

    :param state: Where the workspace stands.
    :param local_sha: Last commit made here, or ``None`` before the first one.
    :param pushed_sha: Last commit the remote confirmed, or ``None``.
    :param unsaved_since: Monotonic timestamp of the oldest commit not yet confirmed remotely.
    :param push_failures: Consecutive failed push attempts, reset by a success.
    :param detail: Why the last attempt failed, empty otherwise.
    :param retriable: Whether a later attempt could get past the recorded failure on its own.
        ``False`` means somebody has to do something -- the branch diverged, the token is bad,
        or the workspace is over the size ceiling.
    :param unreported: A checkpoint that is on the remote but that the control plane has not
        acknowledged. Tracked separately from the push because the fix is different: the work is
        safe, but nothing can yet restore to it.
    """

    state: SaveState = SaveState.IDLE
    local_sha: str | None = None
    pushed_sha: str | None = None
    unsaved_since: float | None = None
    push_failures: int = 0
    detail: str = ""
    retriable: bool = True
    unreported: Checkpoint | None = None

    @property
    def outstanding(self) -> bool:
        """Whether this Runtime holds work that is not yet a durable, restorable checkpoint.

        Deliberately not just "is it pushed". A commit the control plane has never heard of is
        safe from loss but cannot be restored to, and treating that as finished would let the
        next turn build on a point nothing can come back to.
        """
        return (self.local_sha is not None and self.local_sha != self.pushed_sha) or self.unreported is not None

    def unsaved_seconds(self, now: float | None = None) -> float:
        """Age of the oldest unsaved commit, ``0`` when there is none.

        The single most useful number for "is this Runtime falling behind", which is why it is
        exposed instead of only the raw timestamp.
        """
        if self.unsaved_since is None or not self.outstanding:
            return 0.0
        return max(0.0, (time.monotonic() if now is None else now) - self.unsaved_since)

    def as_payload(self, now: float | None = None) -> dict[str, object]:
        """Render for ``/health``."""
        return {
            "state": str(self.state),
            "local_sha": self.local_sha,
            "pushed_sha": self.pushed_sha,
            "unsaved_seconds": round(self.unsaved_seconds(now), 3),
            "push_failures": self.push_failures,
            "detail": self.detail,
            "needs_attention": self.state is SaveState.FAILED and not self.retriable,
            "checkpoint_reported": self.unreported is None,
        }


# Failures a later attempt cannot get past on its own. Retrying a diverged push in a loop would
# spin forever: the remote has moved on, and nothing this Runtime does locally changes that. A
# rejected token is the same story -- it is long-lived, so it will still be rejected next time.
# The next *commit* still tries again, which is what picks these up if somebody fixed the cause
# in the meantime.
_NEEDS_ATTENTION = (GitAuthError, GitDivergedError, GitPolicyError)


class WorkspaceSaver:
    """Commit each turn locally, push in the background, and report how far behind it is.

    Example::

        saver = WorkspaceSaver(workspace)
        await saver.start()
        await saver.commit_turn(run_id="...", conversation_id="...")
        ...
        await saver.aclose()

    :param workspace: The Git working tree to save.
    :param project_id: Recorded on each commit, so a commit can be traced back to its Project.
    :param retry_backoff_seconds: Wait between failed push attempts.
    :param reporter: Told about each checkpoint once it is on the remote. Without one this
        Runtime still saves its files but produces nothing to restore from.
    """

    def __init__(
        self,
        workspace: GitWorkspace,
        *,
        project_id: str = "",
        retry_backoff_seconds: float | None = None,
        reporter: CheckpointReporter | None = None,
    ) -> None:
        self.workspace = workspace
        self.project_id = project_id
        self._reporter = reporter
        self._retry_backoff_seconds = (
            retry_backoff_seconds if retry_backoff_seconds is not None else settings.GIT_PUSH_RETRY_BACKOFF_SECONDS
        )
        self._status = SaveStatus()
        # Which turn the unpushed commits belong to. The newest one names the checkpoint: a push
        # that carries several commits produces one restore point, at the tip.
        self._pending_turn: _Turn | None = None
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        # Serializes the background push against a commit, so the two cannot run git against the
        # same index at once. Held only across the blocking call, never across a wait.
        self._git_lock = asyncio.Lock()

    @property
    def status(self) -> SaveStatus:
        """The current snapshot. Read by ``/health`` and by the pre-run gate."""
        return self._status

    def bind_reporter(self, reporter: CheckpointReporter) -> None:
        """Attach where checkpoints are reported, once there is something to attach.

        Separate from the constructor because a checkpoint has to name the context version the
        commit goes with, and that is read from the Runtime -- which is assembled around this
        saver, and so does not exist yet when it is built.
        """
        self._reporter = reporter

    async def start(self) -> None:
        """Attach the workspace to its remote and begin pushing in the background.

        Attaching can fail -- the remote may be down, or the workspace and the remote may both
        hold content -- and that is recorded rather than raised. A Runtime that refused to start
        would leave the user with no way to be told what went wrong, and no way to keep working
        while somebody fixes it. The failure is visible on ``/health`` and gates the next run.
        """
        if self._task is not None:
            return
        try:
            action = await asyncio.to_thread(self.workspace.ensure_ready)
            logger.info("workspace repository %s", action)
            await asyncio.to_thread(self._adopt_existing_state)
        except GitError as exc:
            self._fail(f"the workspace could not be attached to its Git remote: {exc}")
            logger.exception("attaching the workspace to its Git remote failed")
        self._task = asyncio.create_task(self._loop(), name="workspace-saver")
        # A Runtime reopening a workspace may already hold commits an earlier incarnation never
        # pushed, and nothing else would wake the task until the next turn.
        self._wake.set()

    async def restore_to(self, commit: str) -> RestoreOutcome:
        """Bring the workspace to a conversation's checkpoint before it accepts any run.

        Three outcomes, and the difference between them is the whole point of this method:

        - The branch is already at ``commit``: nothing to do.
        - The branch has moved **past** ``commit``: the Project was developed in another
          conversation since, and that work is kept. Rolling back to this conversation's own
          checkpoint would silently delete somebody else's turns, which is exactly what the plan
          forbids -- a resumed conversation inherits the Project's latest code.
        - ``commit`` is not reachable at all: an explicit failure. Starting on an empty or
          unrelated workspace and letting the model carry on would be the worst of the options,
          because the damage only becomes visible several turns later.

        :param commit: The checkpoint's commit SHA.
        :return: What was done, for the caller to log and report.
        :raises GitError: The commit could not be found, or the remote could not be reached.
        """
        async with self._git_lock:
            head = await asyncio.to_thread(self.workspace.head)
            if head == commit:
                return RestoreOutcome.ALREADY_THERE
            if head is not None and await asyncio.to_thread(self.workspace.is_ancestor, commit, head):
                logger.info(
                    "not restoring to checkpoint %s: this project has been developed since, "
                    "and the newer work at %s is kept",
                    commit,
                    head,
                )
                return RestoreOutcome.SUPERSEDED
            await asyncio.to_thread(self.workspace.restore, commit)
            self._status = SaveStatus(state=SaveState.SAVED, local_sha=commit, pushed_sha=commit)
            return RestoreOutcome.RESTORED

    async def aclose(self) -> None:
        """Stop the background task. Does not push: the caller decides whether to wait."""
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def commit_turn(
        self,
        *,
        run_id: str,
        conversation_id: str,
        context_version: int,
        completed: bool = True,
    ) -> str | None:
        """Record one turn's file changes as a local commit.

        Runs on a worker thread, which is what lets it finish even when the task awaiting it is
        cancelled: the thread is not cancellable, so the commit still lands and still updates
        the status this object reports. The caller may lose the return value; the state survives.

        An interrupted turn is committed too, and says so in its own message. Files the model
        got half-way through writing are worth keeping -- but a later reader must not mistake
        them for the output of a turn that ran to its end.

        :param run_id: The run this commit belongs to.
        :param conversation_id: The conversation the run belongs to.
        :param context_version: Where the turn left the conversation, carried into the checkpoint.
        :param completed: Whether the run's event stream reached its end. ``False`` means the
            client hung up or the task was cancelled part-way through, which says nothing about
            whether the model itself succeeded -- that is the transcript's business, not the
            repository's.
        :return: The new commit's SHA, or ``None`` when the turn changed no files.
        """
        subject = f"App-Spark turn {run_id}" if completed else f"App-Spark turn {run_id} (interrupted)"
        trailers = {
            "Run-Id": run_id,
            "Conversation-Id": conversation_id,
            **({"Project-Id": self.project_id} if self.project_id else {}),
            "Turn-Status": "completed" if completed else "interrupted",
        }
        # The lock covers recording the outcome as well as the git call itself: releasing it in
        # between would let the background push observe -- and confirm -- a commit this object
        # has not registered yet, and then have the registration overwrite the confirmation.
        async with self._git_lock:
            try:
                sha = await asyncio.to_thread(self.workspace.commit, subject, trailers=trailers)
            except GitError as exc:
                self._fail(f"the workspace could not be committed: {exc}")
                logger.exception("committing the workspace failed for run %s", run_id)
                return None
            if sha is None:
                logger.info("run %s changed no files; nothing to save", run_id)
                return None
            self._pending_turn = _Turn(
                run_id=run_id,
                conversation_id=conversation_id,
                context_version=context_version,
            )
            self._record_commit(sha)
        self._wake.set()
        return sha

    async def push_now(self) -> bool:
        """Attempt one push immediately and report whether the remote is now up to date.

        Used by an orderly shutdown, and by tests that would otherwise have to wait for the
        background task. Ordinary turns never call this -- that is the entire point of the split.
        """
        await self._push_once()
        return not self._status.outstanding

    async def _loop(self) -> None:
        """Push whenever there is something outstanding, backing off after a failure."""
        while True:
            await self._wake.wait()
            self._wake.clear()
            try:
                await self._push_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                # A bug here has to be visible, but it must not take the background task down
                # and leave the Runtime quietly never saving again.
                logger.exception("the workspace push task hit an unexpected error")
            if self._should_retry():
                # Raise the flag before sleeping: an idle conversation has no next commit to
                # wake this task, so a retriable failure would otherwise never be retried.
                self._wake.set()
                await asyncio.sleep(self._retry_backoff_seconds)

    def _should_retry(self) -> bool:
        """Whether the last failure is one a later attempt could get past unaided."""
        status = self._status
        return status.outstanding and status.state is SaveState.FAILED and status.retriable

    async def _push_once(self) -> None:
        """Get the outstanding work to the remote and then to the control plane.

        Two steps that fail independently, so they are recovered independently: a commit that is
        pushed does not need pushing again just because reporting it failed. That is also what
        keeps a lost acknowledgement from producing a second, duplicate commit.
        """
        if self._status.local_sha != self._status.pushed_sha and not await self._push_and_pin():
            return
        unreported = self._status.unreported
        if unreported is not None:
            await self._report(unreported)

    async def _push_and_pin(self) -> bool:
        """Push the branch and pin the new tip under its checkpoint tag.

        :return: Whether the work reached the remote.
        """
        async with self._git_lock:
            # Re-checked under the lock: a commit may have landed since the caller looked.
            if self._status.local_sha == self._status.pushed_sha:
                return True
            turn = self._pending_turn
            self._status = replace(self._status, state=SaveState.PUSHING, detail="")
            try:
                pushed = await asyncio.to_thread(self.workspace.push)
                # Pinned after the push, never before: a tag on a commit the remote does not
                # have would be a checkpoint pointing at nothing.
                tag = checkpoint_tag(turn.run_id) if turn is not None else ""
                if tag:
                    await asyncio.to_thread(self.workspace.tag_checkpoint, tag, pushed)
            except _NEEDS_ATTENTION as exc:
                self._fail(str(exc), retriable=False)
                # With the traceback, because this one is going to need somebody to read it.
                logger.exception("the workspace could not be pushed and retrying will not help")
                return False
            except GitError as exc:
                self._fail(str(exc))
                logger.warning("pushing the workspace failed, will retry: %s", exc)
                return False
            self._record_push(pushed, turn=turn, tag=tag)
        logger.info("the workspace is saved remotely at %s", pushed)
        return True

    async def _report(self, checkpoint: Checkpoint) -> None:
        """Tell the control plane about a checkpoint that is fully on the remote.

        Retried with the *same* checkpoint rather than by making another commit: the work is
        already durable, and a second commit would only add an identical tree under a new SHA.
        """
        if self._reporter is None:
            # Nowhere to report to. The commit is on the remote, which is all this Runtime can
            # do about it, so the checkpoint is dropped rather than retried forever.
            self._status = replace(self._status, unreported=None, state=SaveState.SAVED)
            return
        try:
            await self._reporter(checkpoint)
        # Broad on purpose: the reporter is supplied by whoever assembled this saver, and every
        # way it can fail means the same thing here -- the control plane did not take the
        # checkpoint, so try again later. Narrowing would couple this module to the transport.
        except Exception as exc:  # noqa: BLE001
            self._fail(f"the checkpoint could not be reported to the control plane: {exc}")
            logger.warning("reporting checkpoint %s failed, will retry: %s", checkpoint.commit, exc)
            return
        self._status = replace(
            self._status,
            state=SaveState.SAVED,
            unreported=None,
            unsaved_since=None,
            push_failures=0,
            detail="",
        )
        logger.info("checkpoint %s at %s is restorable", checkpoint.tag, checkpoint.commit)

    def _adopt_existing_state(self) -> None:
        """Read the workspace's starting position, once, at startup.

        A Runtime that reopens a workspace inherits whatever the previous one left behind, which
        may include commits that were never pushed.
        """
        head = self.workspace.head()
        if head is None:
            return
        outstanding = self.workspace.unpushed_commits()
        if outstanding:
            self._status = SaveStatus(
                state=SaveState.PENDING,
                local_sha=head,
                pushed_sha=None,
                unsaved_since=time.monotonic(),
            )
            logger.warning("this workspace holds %d commit(s) an earlier Runtime never pushed", outstanding)
        else:
            self._status = SaveStatus(state=SaveState.SAVED, local_sha=head, pushed_sha=head)

    def _record_commit(self, sha: str) -> None:
        self._status = replace(
            self._status,
            state=SaveState.PENDING,
            local_sha=sha,
            # Kept from the first unsaved commit rather than reset on each one, so the age this
            # reports is how long the *oldest* unsaved work has been waiting.
            unsaved_since=self._status.unsaved_since if self._status.outstanding else time.monotonic(),
            detail="",
            retriable=True,
        )

    def _record_push(self, sha: str, *, turn: _Turn | None, tag: str) -> None:
        """Note that ``sha`` is on the remote, and what still has to happen about it."""
        checkpoint = (
            Checkpoint(
                run_id=turn.run_id,
                conversation_id=turn.conversation_id,
                commit=sha,
                tag=tag,
                context_version=turn.context_version,
            )
            if turn is not None and tag
            else None
        )
        self._status = SaveStatus(
            state=SaveState.PUSHING if checkpoint is not None else SaveState.SAVED,
            local_sha=self._status.local_sha or sha,
            pushed_sha=sha,
            # Kept until the checkpoint is reported: until then there is still work whose age is
            # worth watching, even though the files themselves are safe.
            unsaved_since=self._status.unsaved_since if checkpoint is not None else None,
            push_failures=0,
            unreported=checkpoint,
        )

    def _fail(self, detail: str, *, retriable: bool = True) -> None:
        self._status = replace(
            self._status,
            state=SaveState.FAILED,
            push_failures=self._status.push_failures + 1,
            detail=detail,
            retriable=retriable,
            unsaved_since=self._status.unsaved_since or time.monotonic(),
        )
