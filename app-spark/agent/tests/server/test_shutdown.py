"""What a Runtime manages to hand over on its way out.

The drain is the only thing standing between a committed turn and the disposable disk it was
committed on, so these run against real git and a real bare remote: the question is whether the
commit actually reaches the remote, and a stubbed push cannot answer it.

The bound gets its own tests because it is the other half of the guarantee. The control plane
kills a Runtime that overstays its grace period, so a drain that waited as long as it liked
would be killed part-way through and deliver nothing at all.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
from pydantic_ai import Agent

from app_spark_agent.git import WorkspaceSaver
from app_spark_agent.git.errors import GitError
from app_spark_agent.server.runtime import ConversationRuntime
from tests.git.conftest import BRANCH, clone_to, make_workspace, plain_git
from tests.support.fake_models import text_model

# Long enough that the background task is certainly still asleep when the drain runs, so a commit
# that reaches the remote can only have got there by being drained.
IDLE_BACKOFF_SECONDS = 60.0


@pytest.fixture
def bare_remote(tmp_path: Path) -> Path:
    """An empty bare repository standing in for the Project's remote."""
    remote = tmp_path / "remote.git"
    plain_git("init", "--bare", "--initial-branch", BRANCH, str(remote), cwd=tmp_path)
    return remote


def build_runtime(tmp_path: Path, saver: WorkspaceSaver | None) -> ConversationRuntime:
    """Open a Runtime with no control plane, so the drain's only job is the workspace.

    The agent is a stub: ``ConversationRuntime.open`` would otherwise build the production
    DeepSeek one, which these tests never call and which needs an API key they do not have.
    """
    workspace = tmp_path / "workspace"
    state_dir = tmp_path / "state"
    return ConversationRuntime.open(
        workspace=workspace,
        state_dir=state_dir,
        agent=Agent(text_model(("unused",))),
        saver=saver,
    )


async def runtime_owing_a_commit(tmp_path: Path, bare_remote: Path) -> ConversationRuntime:
    """Build a Runtime holding one commit its background task failed to push.

    Produced by moving the remote away and back, which is the closest a local remote gets to a
    host that was briefly unreachable -- and it is the case the drain exists for, because by the
    time the remote returns the background task is deep in its backoff.
    """
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    saver = WorkspaceSaver(
        make_workspace(workspace_dir, bare_remote),
        project_id="proj-1",
        retry_backoff_seconds=IDLE_BACKOFF_SECONDS,
    )
    runtime = build_runtime(tmp_path, saver)
    await saver.start()

    moved = _take_remote_offline(bare_remote)
    (workspace_dir / "note.txt").write_text("written while the host was away\n")
    await saver.commit_turn(run_id="run-1", conversation_id="conv-1", context_version=1)
    # Wait for the failure so the retry is known to be asleep rather than about to happen.
    async with asyncio.timeout(10.0):
        while saver.status.push_failures == 0:  # noqa: ASYNC110
            await asyncio.sleep(0.01)
    _put_remote_back(moved, bare_remote)
    return runtime


def _take_remote_offline(bare_remote: Path) -> Path:
    """Move the remote out from under the workspace, standing in for an unreachable host."""
    moved = bare_remote.parent / "remote-offline.git"
    bare_remote.rename(moved)
    return moved


def _put_remote_back(moved: Path, bare_remote: Path) -> None:
    """Bring the host back, after the background task has already given up on it for a minute."""
    moved.rename(bare_remote)


class TestDrain:
    async def test_it_pushes_the_commit_the_background_task_never_got_to(
        self, tmp_path: Path, bare_remote: Path
    ) -> None:
        runtime = await runtime_owing_a_commit(tmp_path, bare_remote)
        assert runtime.saver is not None

        drained = await runtime.drain(timeout_seconds=10.0)

        assert drained is True
        assert runtime.saver.status.outstanding is False
        await runtime.saver.aclose()
        clone = clone_to(bare_remote, tmp_path / "clone")
        assert (clone / "note.txt").read_text() == "written while the host was away\n"

    async def test_a_runtime_with_nothing_outstanding_drains_immediately(
        self, tmp_path: Path, bare_remote: Path
    ) -> None:
        # Covers the Runtime that has no repository at all as well: both must report caught up
        # rather than make the shutdown wait to find out there was nothing to wait for.
        (tmp_path / "workspace").mkdir()
        runtime = build_runtime(tmp_path, saver=None)

        assert await runtime.drain(timeout_seconds=10.0) is True

    async def test_a_push_that_will_not_finish_cannot_hold_the_shutdown_open(
        self, tmp_path: Path, bare_remote: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runtime = await runtime_owing_a_commit(tmp_path, bare_remote)
        assert runtime.saver is not None

        async def never_returns(_: WorkspaceSaver) -> bool:
            await asyncio.sleep(3600)
            return True

        monkeypatch.setattr(WorkspaceSaver, "push_now", never_returns)
        started = time.monotonic()

        drained = await runtime.drain(timeout_seconds=0.2)

        assert drained is False
        assert time.monotonic() - started < 5.0
        await runtime.saver.aclose()

    async def test_a_push_that_raises_is_reported_rather_than_propagated(
        self, tmp_path: Path, bare_remote: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Nothing the push can do may abort the shutdown: the steps after it still have to run.
        runtime = await runtime_owing_a_commit(tmp_path, bare_remote)
        assert runtime.saver is not None

        async def explodes(_: WorkspaceSaver) -> bool:
            raise GitError("the remote hung up")

        monkeypatch.setattr(WorkspaceSaver, "push_now", explodes)

        assert await runtime.drain(timeout_seconds=10.0) is False
        await runtime.saver.aclose()
