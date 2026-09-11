"""The save state machine: what a turn commits, and what the push reports afterwards.

Runs against real ``git`` and a real bare remote, like the rest of ``tests/git``. The failure
cases are produced by breaking the remote rather than by stubbing git's output, because the
question these tests answer -- "which failures does the saver treat as worth retrying" -- is
only meaningful against the errors git actually emits.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import pytest

from app_spark_agent.git.errors import GitError, GitPolicyError
from app_spark_agent.git.policy import WorkspacePolicy
from app_spark_agent.git.saver import (
    Checkpoint,
    CheckpointReporter,
    RestoreOutcome,
    SaveState,
    SaveStatus,
    WorkspaceSaver,
)
from app_spark_agent.git.workspace import GitWorkspace
from tests.git.conftest import clone_to, make_workspace, plain_git


@pytest.fixture
def saver(workspace: GitWorkspace) -> WorkspaceSaver:
    """A saver with no backoff, so a retry does not make the test wait for it."""
    return WorkspaceSaver(workspace, project_id="proj-1", retry_backoff_seconds=0.0)


async def wait_until(predicate: Callable[[], bool], *, timeout: float = 10.0) -> None:
    """Poll until ``predicate`` holds, so a test never races the background push task.

    Polling rather than an event, deliberately: the thing being waited on is the saver's public
    status, and a test that instead awaited some internal signal would stop checking the one
    surface the server and ``/health`` actually read.
    """
    async with asyncio.timeout(timeout):
        while not predicate():  # noqa: ASYNC110
            await asyncio.sleep(0.01)


async def wait_for_saved(saver: WorkspaceSaver, *, timeout: float = 10.0) -> SaveStatus:
    """Wait for the background task to get everything to the remote."""
    await wait_until(lambda: not saver.status.outstanding, timeout=timeout)
    return saver.status


async def commit_turn(
    saver: WorkspaceSaver,
    *,
    run_id: str,
    conversation_id: str = "conv-1",
    context_version: int = 1,
    completed: bool = True,
) -> str | None:
    """Commit a turn without every test having to name a context version it does not care about.

    The version only matters to the checkpoint, so the tests that are about commits and pushes
    take the default and the ones that are about checkpoints pass their own.
    """
    return await saver.commit_turn(
        run_id=run_id,
        conversation_id=conversation_id,
        context_version=context_version,
        completed=completed,
    )


class TestCommitTurn:
    async def test_a_turn_that_changed_files_is_committed_and_then_pushed(
        self, saver: WorkspaceSaver, workspace_dir: Path, bare_remote: Path, tmp_path: Path
    ) -> None:
        await saver.start()
        (workspace_dir / "app.py").write_text("print('hi')\n")

        sha = await commit_turn(saver, run_id="run-1", conversation_id="conv-1")

        assert sha is not None
        assert saver.status.local_sha == sha
        status = await wait_for_saved(saver)
        assert status.state is SaveState.SAVED
        assert status.pushed_sha == sha
        await saver.aclose()

        clone = clone_to(bare_remote, tmp_path / "clone")
        assert (clone / "app.py").read_text() == "print('hi')\n"

    async def test_a_turn_that_changed_nothing_records_no_commit(
        self, saver: WorkspaceSaver, workspace_dir: Path
    ) -> None:
        await saver.start()
        (workspace_dir / "app.py").write_text("first\n")
        first = await commit_turn(saver, run_id="run-1", conversation_id="conv-1")
        await wait_for_saved(saver)

        # A turn where the model only read files, or just answered a question.
        second = await commit_turn(saver, run_id="run-2", conversation_id="conv-1")

        assert second is None
        assert saver.status.local_sha == first
        assert saver.status.state is SaveState.SAVED
        await saver.aclose()

    async def test_the_commit_records_which_run_produced_it(self, saver: WorkspaceSaver, workspace_dir: Path) -> None:
        await saver.start()
        (workspace_dir / "app.py").write_text("hi\n")

        await commit_turn(saver, run_id="run-7", conversation_id="conv-3")

        message = plain_git("log", "-1", "--format=%B", cwd=workspace_dir)
        assert "App-Spark turn run-7" in message
        assert "Run-Id: run-7" in message
        assert "Conversation-Id: conv-3" in message
        assert "Project-Id: proj-1" in message
        assert "Turn-Status: completed" in message
        await saver.aclose()

    async def test_an_interrupted_turn_is_committed_and_says_so(
        self, saver: WorkspaceSaver, workspace_dir: Path
    ) -> None:
        # A client that hung up mid-turn: the work is worth keeping, but a later reader must not
        # mistake it for the output of a turn that ran to its end.
        await saver.start()
        (workspace_dir / "half.py").write_text("def f(\n")

        sha = await commit_turn(saver, run_id="run-9", conversation_id="conv-1", completed=False)

        assert sha is not None
        message = plain_git("log", "-1", "--format=%B", cwd=workspace_dir)
        assert "(interrupted)" in message
        assert "Turn-Status: interrupted" in message
        await saver.aclose()

    async def test_consecutive_turns_each_produce_a_commit(
        self, saver: WorkspaceSaver, workspace_dir: Path, bare_remote: Path, tmp_path: Path
    ) -> None:
        await saver.start()
        (workspace_dir / "app.py").write_text("one\n")
        await commit_turn(saver, run_id="run-1", conversation_id="conv-1")
        (workspace_dir / "app.py").write_text("two\n")
        await commit_turn(saver, run_id="run-2", conversation_id="conv-1")
        await wait_for_saved(saver)
        await saver.aclose()

        clone = clone_to(bare_remote, tmp_path / "clone")
        assert (clone / "app.py").read_text() == "two\n"
        assert plain_git("rev-list", "--count", "HEAD", cwd=clone).strip() == "2"


class TestUnsavedReporting:
    async def test_an_unreachable_remote_reports_pending_and_saves_once_it_comes_back(
        self, workspace_dir: Path, bare_remote: Path, tmp_path: Path
    ) -> None:
        # The plan's acceptance case: with the network down the turn still completes and the
        # Runtime says the work is unsaved; the save lands on its own once the remote returns.
        saver = WorkspaceSaver(make_workspace(workspace_dir, bare_remote), retry_backoff_seconds=0.01)
        await saver.start()
        moved = _take_remote_offline(bare_remote)
        (workspace_dir / "app.py").write_text("offline\n")

        sha = await commit_turn(saver, run_id="run-1", conversation_id="conv-1")

        assert sha is not None
        await wait_until(lambda: saver.status.push_failures > 0)
        assert saver.status.outstanding
        assert saver.status.state is SaveState.FAILED
        # Retriable: nothing about this failure says the work can never be saved.
        assert saver.status.retriable

        moved.rename(bare_remote)

        status = await wait_for_saved(saver)
        assert status.state is SaveState.SAVED
        assert status.push_failures == 0
        await saver.aclose()

        clone = clone_to(bare_remote, tmp_path / "clone")
        assert (clone / "app.py").read_text() == "offline\n"

    async def test_the_unsaved_age_tracks_the_oldest_commit_not_the_newest(
        self, workspace_dir: Path, bare_remote: Path
    ) -> None:
        saver = WorkspaceSaver(make_workspace(workspace_dir, bare_remote), retry_backoff_seconds=60.0)
        await saver.start()
        moved = _take_remote_offline(bare_remote)
        (workspace_dir / "a.py").write_text("one\n")
        await commit_turn(saver, run_id="run-1", conversation_id="conv-1")
        first_since = saver.status.unsaved_since

        (workspace_dir / "b.py").write_text("two\n")
        await commit_turn(saver, run_id="run-2", conversation_id="conv-1")

        assert saver.status.unsaved_since == first_since
        await saver.aclose()
        moved.rename(bare_remote)

    async def test_a_diverged_remote_is_reported_as_needing_attention(
        self, saver: WorkspaceSaver, workspace_dir: Path, bare_remote: Path, tmp_path: Path
    ) -> None:
        # Retrying cannot get past this, and a saver that spun on it would bury the one signal
        # saying a human has to look.
        await saver.start()
        (workspace_dir / "app.py").write_text("mine\n")
        await commit_turn(saver, run_id="run-1", conversation_id="conv-1")
        await wait_for_saved(saver)

        other = clone_to(bare_remote, tmp_path / "other")
        (other / "theirs.py").write_text("theirs\n")
        plain_git("add", "-A", cwd=other)
        plain_git("commit", "-m", "another writer", cwd=other)
        plain_git("push", "origin", "HEAD:main", cwd=other)

        (workspace_dir / "app.py").write_text("mine again\n")
        await commit_turn(saver, run_id="run-2", conversation_id="conv-1")
        await wait_until(lambda: saver.status.state is SaveState.FAILED)

        assert not saver.status.retriable
        assert saver.status.outstanding
        assert saver.status.as_payload()["needs_attention"] is True
        await saver.aclose()

    async def test_a_file_over_the_size_ceiling_fails_the_commit_loudly(
        self, workspace_dir: Path, bare_remote: Path
    ) -> None:
        workspace = make_workspace(workspace_dir, bare_remote)
        workspace = GitWorkspace(
            path=workspace_dir,
            runner=workspace.runner,
            policy=WorkspacePolicy(max_file_bytes=64),
        )
        saver = WorkspaceSaver(workspace, retry_backoff_seconds=0.0)
        await saver.start()
        (workspace_dir / "huge.bin").write_bytes(b"x" * 128)

        sha = await commit_turn(saver, run_id="run-1", conversation_id="conv-1")

        assert sha is None
        assert saver.status.state is SaveState.FAILED
        # Names the offending path, so the message is actionable without opening a shell.
        assert "huge.bin" in saver.status.detail
        await saver.aclose()


class TestStartup:
    async def test_a_reopened_workspace_pushes_what_the_previous_runtime_left_behind(
        self, workspace_dir: Path, bare_remote: Path, tmp_path: Path
    ) -> None:
        # A Runtime killed between the barrier's commit and the background push. The commit is
        # durable on disk; the next incarnation is what gets it to the remote.
        first = WorkspaceSaver(make_workspace(workspace_dir, bare_remote), retry_backoff_seconds=60.0)
        await first.start()
        moved = _take_remote_offline(bare_remote)
        (workspace_dir / "app.py").write_text("unpushed\n")
        sha = await commit_turn(first, run_id="run-1", conversation_id="conv-1")
        await first.aclose()
        moved.rename(bare_remote)

        reopened = WorkspaceSaver(make_workspace(workspace_dir, bare_remote), retry_backoff_seconds=0.0)
        await reopened.start()

        assert reopened.status.local_sha == sha
        status = await wait_for_saved(reopened)
        assert status.pushed_sha == sha
        await reopened.aclose()

        clone = clone_to(bare_remote, tmp_path / "clone")
        assert (clone / "app.py").read_text() == "unpushed\n"

    async def test_an_unreachable_remote_at_startup_is_reported_rather_than_raised(
        self, workspace_dir: Path, bare_remote: Path
    ) -> None:
        # Refusing to start would leave the user with no way of being told what went wrong.
        moved = _take_remote_offline(bare_remote)
        saver = WorkspaceSaver(make_workspace(workspace_dir, bare_remote), retry_backoff_seconds=60.0)

        await saver.start()

        assert saver.status.state is SaveState.FAILED
        assert saver.status.detail
        await saver.aclose()
        moved.rename(bare_remote)


class TestPolicyReporting:
    def test_the_policy_error_carries_the_offending_paths(self, workspace_dir: Path, bare_remote: Path) -> None:
        base = make_workspace(workspace_dir, bare_remote)
        workspace = GitWorkspace(path=workspace_dir, runner=base.runner, policy=WorkspacePolicy(max_file_bytes=64))
        workspace.ensure_ready()
        (workspace_dir / "huge.bin").write_bytes(b"x" * 128)

        with pytest.raises(GitPolicyError) as excinfo:
            workspace.commit("nope")

        assert excinfo.value.paths == ("huge.bin",)


class TestCheckpointReporting:
    """What a saved turn tells the control plane, and when it is allowed to call itself saved."""

    async def test_a_pushed_turn_is_reported_with_its_tag_and_context_version(
        self, saver: WorkspaceSaver, workspace_dir: Path
    ) -> None:
        reported: list[Checkpoint] = []
        saver.bind_reporter(_collect(reported))
        await saver.start()
        (workspace_dir / "app.py").write_text("print('hi')\n")

        sha = await commit_turn(saver, run_id="run-1", context_version=4)
        await wait_for_saved(saver)

        assert [(point.commit, point.tag, point.context_version) for point in reported] == [
            (sha, "app-spark/checkpoint/run-1", 4)
        ]
        await saver.aclose()

    async def test_the_tag_is_on_the_remote_so_the_commit_cannot_be_collected(
        self, saver: WorkspaceSaver, workspace_dir: Path, bare_remote: Path
    ) -> None:
        # The reason a checkpoint stores a tag at all: a bare SHA that nothing points at is
        # something the remote may reclaim, and then the "restore point" restores nothing.
        await saver.start()
        (workspace_dir / "app.py").write_text("print('hi')\n")

        sha = await commit_turn(saver, run_id="run-1")
        await wait_for_saved(saver)

        pinned = plain_git("rev-parse", "app-spark/checkpoint/run-1^{commit}", cwd=bare_remote)
        assert pinned.strip() == sha

    async def test_a_turn_is_not_saved_until_its_checkpoint_has_been_taken(
        self, saver: WorkspaceSaver, workspace_dir: Path
    ) -> None:
        """ "Saved" has to mean restorable, not merely durable.

        A reporter that keeps failing leaves the files safely on the remote and the checkpoint
        nowhere, and resuming from a commit nothing recorded is not something anyone can do. So
        the turn stays outstanding, which is what the pre-run gate reads.
        """
        attempts = 0

        async def refuse(_: Checkpoint) -> None:
            nonlocal attempts
            attempts += 1
            raise RuntimeError("the control plane is not answering")

        saver.bind_reporter(refuse)
        await saver.start()
        (workspace_dir / "app.py").write_text("print('hi')\n")

        await commit_turn(saver, run_id="run-1")
        await wait_until(lambda: attempts >= 2)

        assert saver.status.outstanding
        assert saver.status.pushed_sha == saver.status.local_sha
        await saver.aclose()

    async def test_a_retried_report_carries_the_same_commit_rather_than_a_new_one(
        self, saver: WorkspaceSaver, workspace_dir: Path
    ) -> None:
        """The work is already on the remote; committing again would only duplicate the tree."""
        seen: list[Checkpoint] = []

        async def refuse_once(checkpoint: Checkpoint) -> None:
            seen.append(checkpoint)
            if len(seen) == 1:
                raise RuntimeError("lost the acknowledgement")

        saver.bind_reporter(refuse_once)
        await saver.start()
        (workspace_dir / "app.py").write_text("print('hi')\n")

        await commit_turn(saver, run_id="run-1")
        await wait_for_saved(saver)

        assert len(seen) == 2
        assert seen[0] == seen[1]
        await saver.aclose()


class TestRestore:
    """Putting a workspace back, and the two cases where putting it back would be wrong."""

    async def test_a_workspace_behind_its_checkpoint_is_moved_forward(
        self, saver: WorkspaceSaver, workspace_dir: Path
    ) -> None:
        """The case the restore exists for: files that do not go as far as the conversation.

        Reproduced by walking the working tree back, which is what a recycled sandbox holding an
        older snapshot of the same repository looks like from here.
        """
        await saver.start()
        (workspace_dir / "app.py").write_text("first\n")
        first = await commit_turn(saver, run_id="run-1")
        await wait_for_saved(saver)
        (workspace_dir / "app.py").write_text("second\n")
        second = await commit_turn(saver, run_id="run-2")
        await wait_for_saved(saver)
        await saver.aclose()
        plain_git("reset", "--hard", str(first), cwd=workspace_dir)

        assert second is not None
        outcome = await saver.restore_to(second)

        assert outcome is RestoreOutcome.RESTORED
        assert (workspace_dir / "app.py").read_text() == "second\n"

    async def test_a_workspace_already_at_the_checkpoint_is_left_alone(
        self, saver: WorkspaceSaver, workspace_dir: Path
    ) -> None:
        await saver.start()
        (workspace_dir / "app.py").write_text("first\n")
        sha = await commit_turn(saver, run_id="run-1")
        await wait_for_saved(saver)
        await saver.aclose()

        assert sha is not None
        assert await saver.restore_to(sha) is RestoreOutcome.ALREADY_THERE

    async def test_newer_work_is_not_rolled_back_to_an_older_checkpoint(
        self, saver: WorkspaceSaver, workspace_dir: Path
    ) -> None:
        """Reopening an old conversation must not undo what the Project did since.

        A checkpoint records where *that conversation* left the files, not where the Project is.
        Rolling the workspace back to it would delete another conversation's work, which is a
        far worse outcome than the model finding files it does not remember writing.
        """
        await saver.start()
        (workspace_dir / "app.py").write_text("first\n")
        old = await commit_turn(saver, run_id="run-1")
        await wait_for_saved(saver)
        (workspace_dir / "later.py").write_text("somebody else's turn\n")
        await commit_turn(saver, run_id="run-2")
        await wait_for_saved(saver)
        await saver.aclose()

        assert old is not None
        outcome = await saver.restore_to(old)

        assert outcome is RestoreOutcome.SUPERSEDED
        assert (workspace_dir / "later.py").exists()

    async def test_a_commit_the_remote_does_not_have_fails_loudly(
        self, saver: WorkspaceSaver, workspace_dir: Path
    ) -> None:
        """Better to refuse than to start a fresh, empty workspace as if nothing were missing."""
        await saver.start()
        (workspace_dir / "app.py").write_text("first\n")
        await commit_turn(saver, run_id="run-1")
        await wait_for_saved(saver)
        await saver.aclose()

        with pytest.raises(GitError):
            await saver.restore_to("0" * 40)


def _collect(sink: list[Checkpoint]) -> CheckpointReporter:
    """An async reporter that just remembers what it was told."""

    async def report(checkpoint: Checkpoint) -> None:
        sink.append(checkpoint)

    return report


class TestStatusSnapshot:
    def test_an_untouched_workspace_reports_nothing_outstanding(self) -> None:
        assert SaveStatus().outstanding is False
        assert SaveStatus().unsaved_seconds() == 0.0

    def test_a_pushed_commit_is_not_outstanding(self) -> None:
        status = SaveStatus(state=SaveState.SAVED, local_sha="abc", pushed_sha="abc")
        assert status.outstanding is False

    def test_the_age_is_measured_from_the_oldest_unsaved_commit(self) -> None:
        status = SaveStatus(state=SaveState.PENDING, local_sha="abc", unsaved_since=100.0)
        assert status.unsaved_seconds(now=142.0) == 42.0

    def test_the_payload_carries_the_signals_an_operator_needs(self) -> None:
        status = SaveStatus(
            state=SaveState.FAILED,
            local_sha="abc",
            unsaved_since=100.0,
            push_failures=3,
            detail="boom",
            retriable=False,
        )

        payload = status.as_payload(now=130.0)

        assert payload["unsaved_seconds"] == 30.0
        assert payload["push_failures"] == 3
        assert payload["needs_attention"] is True


def _take_remote_offline(bare_remote: Path) -> Path:
    """Move the remote out from under the workspace, standing in for an unreachable host.

    A path that stopped resolving is the closest a local remote gets to a network partition, and
    it exercises the same branch: git fails the transport, and the saver has to decide what that
    means for the work already committed.

    :return: Where the remote went, so the test can put it back.
    """
    moved = bare_remote.parent / "remote-offline.git"
    bare_remote.rename(moved)
    return moved
