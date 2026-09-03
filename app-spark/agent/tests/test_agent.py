from pathlib import Path
from typing import Any, cast

import pytest
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai_harness import (
    ClampOversizedMessages,
    ClearToolResults,
    DeduplicateFileReads,
    FileSystem,
    Shell,
    SummarizingCompaction,
    TieredCompaction,
)
from pydantic_ai_harness.repo_context import RepoContext
from pydantic_ai_harness.shell import LLM_API_KEY_ENV_PATTERNS
from pytest import MonkeyPatch

from app_spark_agent import settings
from app_spark_agent.agent import build_compaction, build_model, create_agent, file_read_key


def test_create_agent_scopes_tools_to_workspace(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "MODEL_API_KEY", "not-used-by-this-test")

    agent = create_agent(tmp_path)

    assert isinstance(agent.model, OpenAIChatModel)
    assert agent.model.model_name == "deepseek-v4-flash"
    assert agent.model.provider is not None
    assert agent.model.provider.name == "deepseek"
    assert settings.MODEL == "deepseek:deepseek-v4-flash"

    capabilities = agent.root_capability.capabilities
    filesystem = next(item for item in capabilities if isinstance(item, FileSystem))
    shell = next(item for item in capabilities if isinstance(item, Shell))
    repo_context = next(item for item in capabilities if isinstance(item, RepoContext))

    assert Path(filesystem.root_dir) == tmp_path
    assert Path(shell.cwd) == tmp_path
    # The harness's own key patterns are extended, not replaced. Which vendors that list names
    # is the harness's business and it does change, so the assertion is that this runtime adds
    # its prefix to the list rather than passing a list of its own -- doing the latter would
    # silently hand every provider key to the model's shell commands.
    assert set(LLM_API_KEY_ENV_PATTERNS) <= set(shell.denied_env_patterns)
    assert "APP_SPARK_AGENT_*" in shell.denied_env_patterns
    assert repo_context.workspace_dir == tmp_path
    assert repo_context.nested_traversal is True
    assert tuple(repo_context.filenames) == ("AGENTS.md",)
    assert any(isinstance(item, TieredCompaction) for item in capabilities)


def test_the_configured_api_key_reaches_the_provider(monkeypatch: MonkeyPatch) -> None:
    """A key that only exists in the settings must still authenticate the provider.

    The value never enters ``os.environ``, so a provider left to read the environment
    itself would come up empty.
    """
    monkeypatch.setattr(settings, "MODEL_API_KEY", "key-only-in-settings")

    model = build_model()

    assert isinstance(model, OpenAIChatModel)
    client = cast(Any, model.client)
    assert client.api_key == "key-only-in-settings"


def test_compaction_escalates_from_cheap_to_expensive() -> None:
    """The summarizing tier costs a model call, so it must be the last resort, not the first."""
    compaction = build_compaction()

    assert [type(tier) for tier in compaction.tiers] == [
        ClampOversizedMessages,
        DeduplicateFileReads,
        ClearToolResults,
        SummarizingCompaction,
    ]
    # An absolute budget rather than a fraction of the window; `test_settings.py` pins why that
    # number is what it is.
    assert compaction.target_tokens == settings.COMPACTION_TARGET_TOKENS


def test_file_read_key_matches_the_harness_read_tool() -> None:
    """A wrong tool name silently disables deduplication; a wrong path blanks live data."""
    # `get_toolset` is typed as the filtered wrapper, so reach the registry through `Any`.
    toolset = cast(Any, FileSystem(root_dir=Path.cwd()).get_toolset())
    assert "read_file" in toolset.tools

    assert file_read_key(ToolCallPart(tool_name="read_file", args={"path": "a.py"})) == "a.py"
    assert file_read_key(ToolCallPart(tool_name="write_file", args={"path": "a.py"})) is None
    # `ClampOversizedMessages` replaces oversized arguments, leaving no path to key on.
    assert file_read_key(ToolCallPart(tool_name="read_file", args={"clamped": True})) is None


def test_file_tools_cannot_see_sibling_state_dir(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """File tools are rooted at workspace and cannot list or read sibling state."""
    workspace = tmp_path / "workspace"
    state_dir = tmp_path / "state"
    workspace.mkdir()
    state_dir.mkdir()
    (state_dir / "context.json").write_text('{"secret": true}')

    monkeypatch.setattr(settings, "MODEL_API_KEY", "not-used-by-this-test")
    agent = create_agent(workspace)
    filesystem = next(item for item in agent.root_capability.capabilities if isinstance(item, FileSystem))
    assert Path(filesystem.root_dir) == workspace.resolve()
    toolset = cast(Any, filesystem.get_toolset())
    inner = getattr(toolset, "wrapped", toolset)
    while hasattr(inner, "wrapped"):
        inner = inner.wrapped

    workspace_names = {path.name for path in workspace.iterdir()}
    assert "context.json" not in workspace_names
    assert "state" not in workspace_names

    for outside in (f"../{state_dir.name}/context.json", str(state_dir / "context.json")):
        with pytest.raises((PermissionError, ModelRetry), match="outside"):
            inner._resolve_path(outside)


def test_create_agent_rejects_file_workspace(tmp_path: Path) -> None:
    path = tmp_path / "file"
    path.write_text("content")

    try:
        create_agent(path)
    except NotADirectoryError as exc:
        assert str(path) in str(exc)
    else:
        raise AssertionError("create_agent should reject a file workspace")
