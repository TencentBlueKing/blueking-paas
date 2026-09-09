"""Construction of the workspace-scoped coding agent."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Protocol, cast

import httpx2
from openai import AsyncOpenAI, DefaultAsyncHttpxClient
from pydantic_ai import Agent
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.messages import ModelMessage, ToolCallPart
from pydantic_ai.models import Model, infer_model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers import Provider, infer_provider_class
from pydantic_ai.providers.openai import OpenAIProvider
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
from app_spark_agent.app_log import AppLogReader, AppLogReadResult
from app_spark_agent.bkaidev.auth import (
    OPENAI_API_KEY_PLACEHOLDER,
    WithoutAuthorization,
    authorization_headers,
)
from app_spark_agent.fake_model import FAKE_MODEL_PREFIX, build_fake_model
from app_spark_agent.skills import SKILLS_DIR


class ApiKeyProvider(Protocol):
    """A provider class that authenticates with a plain API key."""

    def __call__(self, *, api_key: str) -> Provider[Any]: ...


def build_model() -> Model:
    """Build the chat model the agent will call."""

    # fake: 不发起网络请求。infer_model 只特殊处理 "test"，其它未知前缀会直接拒。
    if settings.MODEL.startswith(FAKE_MODEL_PREFIX):
        return build_fake_model(settings.MODEL.removeprefix(FAKE_MODEL_PREFIX))

    token = settings.gateway_access_token()
    base_url = settings.MODEL_BASE_URL.strip()
    model_name = settings.resolved_model_name()
    profile = settings.openai_capability_profile(model_name)

    # 网关三件套：token + 地址 + 对照表内模型。协议仍是 Chat Completions，鉴权换头。
    if token and base_url and profile is not None:
        return _build_gateway_model(model_name, base_url, token, profile=profile)

    # 没有网关意图、只注入了 MODEL_API_KEY：官网 / 单测直连。
    if settings.uses_direct_provider():
        return _build_inferred_model()

    # 缺项不推断、也不发往公网；占位模型让进程能起来、/health 能答。
    return _build_unready_model()


def _build_gateway_model(
    model_name: str,
    base_url: str,
    access_token: str,
    *,
    profile: OpenAIModelProfile,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> OpenAIChatModel:
    """用 OpenAI 兼容客户端拨 bkaidev。

    api_key 只填占位 empty，过网关靠 X-Bkapi-Authorization。profile 必须由调用方
    传入（对照表里那份打开了 tools / JSON 输出的档），不能交给 pydantic-ai 按名字
    猜——表外或保守推断会把工具调用静默关掉，进程看起来正常，模型却调不了工具。
    """
    client = AsyncOpenAI(
        base_url=base_url,
        api_key=OPENAI_API_KEY_PLACEHOLDER,
        default_headers=authorization_headers(access_token),
        http_client=DefaultAsyncHttpxClient(transport=WithoutAuthorization(transport)),
    )
    return OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(openai_client=client),
        profile=profile,
    )


async def _unready_stream(_messages: list[ModelMessage], _info: AgentInfo) -> AsyncIterator[str]:
    """未就绪占位：被调用说明门闩被绕过了。"""
    raise RuntimeError("model is not ready: need access_token, MODEL_BASE_URL, and a listed MODEL_NAME")
    yield ""


def _build_unready_model() -> FunctionModel:
    """让 create_agent 在未就绪时仍能构造，避免进程起不来、/health 答不上。"""
    return FunctionModel(stream_function=_unready_stream, model_name="unready")


def _build_inferred_model() -> Model:
    """<provider>:<model> 推断路径，单测和官网直连预留。"""

    def provider_factory(provider_name: str) -> Provider[Any]:
        provider_class = infer_provider_class(provider_name)
        if settings.MODEL_API_KEY is None:
            # No configured key: fall back to whatever variable the provider reads itself.
            return provider_class()

        return cast(ApiKeyProvider, provider_class)(api_key=settings.MODEL_API_KEY)

    return infer_model(settings.MODEL, provider_factory=provider_factory)


def file_read_key(call: ToolCallPart) -> str | None:
    """Return the path a file-read tool call refers to, or None for any other call.

    DeduplicateFileReads ships no default because a wrong guess would blank live data, so
    this maps the harness FileSystem read tool explicitly. Clamped arguments carry no
    path, which correctly reads as "not a file read" rather than as a read of nothing.
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
    TieredCompaction, which drives them directly.

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


def create_agent(workspace: str | Path, *, state_dir: Path | None = None) -> Agent[None, str]:
    """Create the coding agent scoped to workspace.

    The harness file tools enforce a workspace root and protect common secrets. Shell commands
    are useful for development but are not an operating-system sandbox, so this runtime must only
    be used with trusted users and workspaces. The application log tool reads one path outside
    both workspace and state_dir.

    :param workspace: Existing directory the agent may inspect and modify.
    :param state_dir: Conversation state directory; the log tool must not point inside it.
    :return: A configured Pydantic AI coding agent.
    :raises NotADirectoryError: If workspace is not an existing directory.
    """
    workspace_path = Path(workspace).expanduser().resolve(strict=True)
    if not workspace_path.is_dir():
        raise NotADirectoryError(f"Workspace is not a directory: {workspace_path}")

    resolved_state = state_dir.expanduser().resolve() if state_dir is not None else None
    reader = AppLogReader(
        Path(settings.APP_LOG_PATH),
        workspace=workspace_path,
        state_dir=resolved_state,
    )

    def read_app_log() -> AppLogReadResult:
        """Read this session's application log. The path is not a parameter."""
        return reader.read()

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
        RepoContext(
            workspace_dir=SKILLS_DIR,
            filenames=("fastapi_http.md",),
            nested_traversal=False,
            expose_inventory_tool=False,
        ),
        build_compaction(),
    ]
    return Agent(
        build_model(),
        instructions=settings.INSTRUCTIONS,
        capabilities=capabilities,
        tools=[read_app_log],
    )
