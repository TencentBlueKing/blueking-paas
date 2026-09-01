"""Fixtures that put a real Runtime process in front of a scenario.

Shared by :mod:`tests.e2e`, which drives the real model, and :mod:`tests.live`, which drives
the ``fake:`` scenarios. The two differ only in what they cost and therefore in whether they
demand an API key, so everything except that gate lives here.

They are imported into each suite's ``conftest.py`` rather than registered as a plugin, because
``pytest_plugins`` is only honoured in the rootdir conftest.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import pytest

from tests.support import console
from tests.support.live import LiveRuntime, serve


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

    Every Runtime a test starts is registered for shutdown here, including the ones a scenario
    starts for itself: the restart and cold-restore stories run two and three processes, and a
    scenario that fails halfway must not leave any of them behind.
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
def conversation_id() -> str:
    """The conversation every turn of one scenario belongs to."""
    conversation_id = str(uuid4())
    console.note(f"conversation={conversation_id}")
    return conversation_id
