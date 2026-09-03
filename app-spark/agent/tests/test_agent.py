import fnmatch
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic_ai import Agent
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


def denied(name: str, patterns: Sequence[str]) -> bool:
    """Whether a subprocess would inherit ``name``, decided the way the harness decides it."""
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def shell_of(agent: Agent[None, str]) -> Shell:
    return next(item for item in agent.root_capability.capabilities if isinstance(item, Shell))


@pytest.mark.parametrize(
    "name",
    [
        "APP_SPARK_AGENT_MODEL_API_KEY",
        "APP_SPARK_AGENT_RUNTIME_TOKEN",
    ],
)
def test_a_credential_is_stripped_from_the_environment_a_subprocess_inherits(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    name: str,
) -> None:
    """The first layer of credential protection: the model's shell never sees the value.

    Asserted against `fnmatch`, the matcher the harness itself uses, rather than against the
    literal pattern list -- what matters is whether the name is excluded, not how it is spelled.
    """
    monkeypatch.setattr(settings, "MODEL_API_KEY", "not-used-by-this-test")

    patterns = shell_of(create_agent(tmp_path)).denied_env_patterns

    assert denied(name, patterns)


def provider_key_of(model: Any) -> str:
    """Return the credential the built model's provider client will authenticate with."""
    assert isinstance(model, OpenAIChatModel)
    return cast(str, cast(Any, model.client).api_key)


def test_the_injected_contract_key_reaches_the_provider(monkeypatch: MonkeyPatch) -> None:
    """`APP_SPARK_AGENT_MODEL_API_KEY` alone must be enough to start the provider."""
    monkeypatch.setattr(settings, "MODEL_API_KEY", "injected-contract-key")

    assert provider_key_of(build_model()) == "injected-contract-key"


def test_the_settings_key_reaches_the_provider_when_it_is_not_in_the_environment(
    monkeypatch: MonkeyPatch,
) -> None:
    """A key that only exists in the settings must still authenticate the provider.

    The value never enters ``os.environ``, so a provider left to read the environment
    itself would come up empty.
    """
    monkeypatch.setattr(settings, "MODEL_API_KEY", "key-only-in-settings")

    assert provider_key_of(build_model()) == "key-only-in-settings"


def test_compaction_escalates_from_cheap_to_expensive() -> None:
    """The summarizing tier costs a model call, so it must be the last resort, not the first."""
    compaction = build_compaction()

    assert [type(tier) for tier in compaction.tiers] == [
        ClampOversizedMessages,
        DeduplicateFileReads,
        ClearToolResults,
        SummarizingCompaction,
    ]
    # An absolute budget rather than a fraction of the window; `settings.py` pins why that
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
