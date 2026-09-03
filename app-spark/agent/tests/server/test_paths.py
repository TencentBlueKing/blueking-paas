"""Container path lock: workspace and state stay distinct; overlap refuses to start."""

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from app_spark_agent import settings
from app_spark_agent.server.runtime import ConversationRuntime


def test_container_default_paths_are_locked_siblings() -> None:
    assert settings.DEFAULT_WORKSPACE == "/data/workspace"
    assert settings.DEFAULT_STATE_DIR == "/data/state"
    assert settings.DEFAULT_WORKSPACE != settings.DEFAULT_STATE_DIR


@pytest.mark.parametrize(
    "state_for",
    [
        pytest.param(lambda workspace: workspace / "state", id="state-inside-workspace"),
        pytest.param(lambda workspace: workspace, id="identical-paths"),
    ],
)
def test_open_rejects_overlapping_state(tmp_path: Path, state_for: Callable[[Path], Path]) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    agent = Agent(TestModel())
    with pytest.raises(ValueError, match="outside the workspace"):
        ConversationRuntime.open(workspace=workspace, state_dir=state_for(workspace), agent=agent)
