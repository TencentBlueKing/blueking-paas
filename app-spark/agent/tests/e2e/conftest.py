"""Fixtures that put a real Runtime in front of a live scenario.

Every Runtime a test starts is registered for shutdown here, including the ones a scenario
starts for itself: the restart and cold-restore stories run two and three processes, and a
scenario that fails halfway must not leave any of them behind.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import pytest

from app_spark_agent import settings
from tests.e2e import console
from tests.e2e.live import LiveRuntime, serve


@pytest.fixture(autouse=True)
def require_api_key() -> None:
    """Skip rather than fail when there is no key: these tests spend real money and time."""
    if not settings.MODEL_API_KEY:
        pytest.skip("APP_SPARK_AGENT_MODEL_API_KEY is required by the live tests")


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """An empty directory the agent is allowed to write in."""
    path = tmp_path / "workspace"
    path.mkdir()
    return path


class StartRuntime(Protocol):
    """Start one Runtime, on its own state directory, with optional settings overrides."""

    def __call__(self, *, state: str = "runtime", **overrides: str) -> LiveRuntime: ...


@pytest.fixture
def start_runtime(workspace: Path, tmp_path: Path) -> Iterator[StartRuntime]:
    """Return a factory for live Runtimes sharing one workspace.

    ``state`` names the directory the conversation is persisted in, which is the only thing a
    restart has to keep and a cold Runtime has to be denied: passing the same name twice
    reopens the same state, a new name starts an empty one.
    """
    with ExitStack() as running:

        def start(*, state: str = "runtime", **overrides: str) -> LiveRuntime:
            return running.enter_context(
                serve(
                    workspace=workspace,
                    state_dir=tmp_path / state,
                    label=state,
                    **overrides,
                )
            )

        yield start


@pytest.fixture
def runtime(start_runtime: StartRuntime) -> LiveRuntime:
    """One Runtime on production settings, with an empty workspace and no history."""
    return start_runtime()


@pytest.fixture
def conversation_id() -> str:
    """The conversation every turn of one scenario belongs to."""
    conversation_id = str(uuid4())
    console.note(f"conversation={conversation_id}")
    return conversation_id
