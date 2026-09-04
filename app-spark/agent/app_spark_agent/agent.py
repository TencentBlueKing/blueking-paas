"""Construction of the workspace-scoped coding agent."""

from pathlib import Path
from typing import Any, Protocol, cast

from pydantic_ai import Agent
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models import Model, infer_model
from pydantic_ai.providers import Provider, infer_provider_class
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

from app_spark_agent import settings


class ApiKeyProvider(Protocol):
    """A provider class that authenticates with a plain API key."""

    def __call__(self, *, api_key: str) -> Provider[Any]: ...


def build_model() -> Model:
    """Build the model named by :data:`app_spark_agent.settings.MODEL`."""

    def provider_factory(provider_name: str) -> Provider[Any]:
        provider_class = infer_provider_class(provider_name)
        if settings.MODEL_API_KEY is None:
            # No configured key: fall back to whatever variable the provider reads itself.
            return provider_class()

        return cast(ApiKeyProvider, provider_class)(api_key=settings.MODEL_API_KEY)

    return infer_model(settings.MODEL, provider_factory=provider_factory)


def file_read_key(call: ToolCallPart) -> str | None:
    """Return the path a file-read tool call refers to, or ``None`` for any other call.

    ``DeduplicateFileReads`` ships no default because a wrong guess would blank live data, so
    this maps the harness ``FileSystem`` read tool explicitly. Clamped arguments carry no
    ``path``, which correctly reads as "not a file read" rather than as a read of nothing.
    """
    if call.tool_name != "read_file":
        return None
    path = call.args_as_dict().get("path")
    return path if isinstance(path, str) else None


def build_compaction() -> TieredCompaction[object]:
    """Build the escalation used to keep a long conversation inside the context window.

    Tiers run cheap-to-expensive and stop as soon as the history fits the target, so the
    summarizing tier -- the only one that spends a model call -- is reached only when blanking
    and deduplicating cannot reclaim enough. Each tier's own trigger is ignored inside
    ``TieredCompaction``, which drives them directly.

    :return: The tiered compaction capability the agent is built with.
    """
    return TieredCompaction[object](
        tiers=[
            ClampOversizedMessages[object](max_part_tokens=settings.COMPACTION_MAX_PART_TOKENS),
            DeduplicateFileReads[object](file_key=file_read_key),
            ClearToolResults[object](
                max_tokens=1,
                keep_pairs=settings.COMPACTION_KEEP_TOOL_RESULT_PAIRS,
            ),
            SummarizingCompaction[object](
                max_messages=1,
                keep_messages=settings.COMPACTION_KEEP_MESSAGES,
                keep_user_messages=True,
            ),
        ],
        target_tokens=settings.COMPACTION_TARGET_TOKENS,
    )


def create_agent(workspace: str | Path) -> Agent[None, str]:
    """Create the coding agent scoped to ``workspace``.

    The harness file tools enforce a workspace root and protect common secrets. Shell commands
    are useful for development but are not an operating-system sandbox, so this runtime must only
    be used with trusted users and workspaces.

    :param workspace: Existing directory the agent may inspect and modify.
    :return: A configured Pydantic AI coding agent.
    :raises NotADirectoryError: If ``workspace`` is not an existing directory.
    """
    workspace_path = Path(workspace).expanduser().resolve(strict=True)
    if not workspace_path.is_dir():
        raise NotADirectoryError(f"Workspace is not a directory: {workspace_path}")

    capabilities: list[AbstractCapability[object]] = [
        FileSystem(root_dir=workspace_path),
        Shell(
            cwd=workspace_path,
            denied_env_patterns=(
                *LLM_API_KEY_ENV_PATTERNS,
                "APP_SPARK_AGENT_*",
            ),
        ),
        RepoContext(
            workspace_dir=workspace_path,
            filenames=("AGENTS.md",),
            nested_traversal=True,
        ),
        build_compaction(),
    ]
    return Agent(build_model(), instructions=settings.INSTRUCTIONS, capabilities=capabilities)
