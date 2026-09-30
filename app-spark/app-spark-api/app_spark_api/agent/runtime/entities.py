# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Value objects exchanged with an Agent Runtime, and the providers' configuration."""

from __future__ import annotations

import posixpath
from collections.abc import Awaitable, Callable
from pathlib import PurePosixPath
from typing import Any, Literal

import attrs

from app_spark_api.agent.runtime.constants import ENV_PREFIX, MODEL_ENV_NAMES
from app_spark_api.agent.runtime.exceptions import (
    AgentConfigurationError,
    AgentUnavailableError,
    ModelAccessConfigurationError,
)
from app_spark_api.utils import structure_config, validate_non_empty_string

# How long a sandbox outlives its Agent's idle exit. The Agent's orderly shutdown takes at most
# 20 seconds (its own hard-exit deadline); the rest covers clock skew between this service and
# the sandbox, and a turn's end renewal landing a little before the Agent resets its idle timer.
IDLE_EXIT_MARGIN_SECONDS = 60


def validate_agent_extra_env(_: object, attribute: attrs.Attribute[dict[str, str]], value: dict[str, str]) -> None:
    """Validate the extra variables a provider hands to the Agent Runtime it starts.

    :param attribute: Metadata for the attrs field being validated.
    :param value: Variable names mapped to their values.
    :raises ValueError: If a name is outside ``APP_SPARK_AGENT_*`` or is a model variable.
    """
    # 只放行 agent 自己的配置：本服务的其它变量（尤其是 APP_SPARK_API_* 里的平台密钥）不能借
    # 这个口子流进 Runtime。
    foreign = sorted(name for name in value if not name.startswith(ENV_PREFIX))
    if foreign:
        raise ValueError(f"{attribute.name} may only hold {ENV_PREFIX}* variables, got {foreign}")

    owned = sorted(MODEL_ENV_NAMES.intersection(value))
    if owned:
        raise ValueError(f"{attribute.name} must not set model variables, use the model source settings: {owned}")


def validate_sandbox_path(_: object, attribute: attrs.Attribute[str], value: str) -> None:
    """Validate an absolute path inside a sandbox.

    A relative path would resolve against whatever directory envd happens to start the command
    in, and would slip past the checks that compare paths with each other.

    :param attribute: Metadata for the attrs field being validated.
    :param value: Path to validate.
    :raises ValueError: If the path is empty or not absolute.
    """
    validate_non_empty_string(_, attribute, value)
    if not PurePosixPath(value).is_absolute():
        raise ValueError(f"{attribute.name} must be an absolute path, got {value!r}")


@attrs.frozen
class LocalProcessConfig:
    """Configuration for spawning Agent Runtimes as local processes.

    :param agent_project_dir: Directory holding the agent's ``pyproject.toml``; ``uv run`` is
        pointed at it.
    :param workspace_root: Parent of the per-Project workspace directories.
    :param state_root: Parent of the per-conversation state directories. Must not sit inside
        ``workspace_root``, or the agent's own file tools could corrupt its history.
    :param callback_base_url: Where a spawned Runtime can reach *this* service, to replicate
        its state back. Loopback is right for a process on this host and wrong for anything
        else, which is exactly why it is provider configuration rather than a global setting.
    :param startup_timeout_seconds: How long to wait for a spawned Runtime to answer
        ``/health``.
    :param extra_env: Further ``APP_SPARK_AGENT_*`` variables to hand the process, so an agent
        setting can be reached without growing a field here for each one. Model variables are
        refused: which model a Runtime calls, and with what credential, is the model source's
        decision, not the provider's.
    """

    agent_project_dir: str = attrs.field(validator=validate_non_empty_string)
    workspace_root: str = attrs.field(validator=validate_non_empty_string)
    state_root: str = attrs.field(validator=validate_non_empty_string)
    callback_base_url: str = "http://127.0.0.1:8000"
    startup_timeout_seconds: float = 60.0
    extra_env: dict[str, str] = attrs.field(factory=dict, validator=validate_agent_extra_env)


@attrs.frozen
class E2BConfig:
    """Configuration for provisioning an E2B sandbox per conversation and starting its Agent.

    :param api_key: Credential for the E2B-compatible API.
    :param api_url: Base URL of that API; independent of the exposed port domain.
    :param callback_base_url: Where a Runtime inside the sandbox reaches *this* service to
        replicate its state back, i.e. the service's public address. The state callback path
        is appended with its FORCE_SCRIPT_NAME prefix intact, since the call comes in through
        Ingress.
    :param domain: Fallback domain for sandbox hosts when the API does not return one.
    :param template: Sandbox template name or ID.
    :param idle_timeout_seconds: How long a sandbox may go without a conversation turn before
        it is reclaimed (default 1800). The Agent is told to exit after this long idle, pushing
        its workspace first, and the sandbox's E2B deadline is set this long plus
        IDLE_EXIT_MARGIN_SECONDS from the start and the end of every turn, and periodically
        while one runs.
    :param max_lifetime_seconds: Age after which a sandbox is replaced at the start of the next
        turn (default 86400). A running turn is never interrupted for it. Must stay below the
        E2B platform's own cap on a sandbox's lifetime, by at least the longest turn expected:
        a sandbox just short of this age is reused, and the platform kills it outright, without
        letting the Agent push, once the cap is reached.
    :param runtime_port: Sandbox port the Agent Runtime HTTP server listens on.
    :param preview_port: Fixed sandbox port for the workspace application preview.
    :param port_scheme: URL scheme for the exposed port proxy.
    :param workspace_dir: The Agent's workspace inside the sandbox.
    :param state_dir: The Agent's durable state directory inside the sandbox. Must not sit
        inside ``workspace_dir``, or the agent's own file tools could corrupt its history.
    :param agent_command: Command that starts the Agent Runtime inside the sandbox. It reads
        its port and everything else from ``APP_SPARK_AGENT_*`` variables. Interpreted by bash
        after ``exec``, in an environment that holds the Agent's credentials, so it is trusted
        operator configuration and must be a single command, not a pipeline or a sequence.
    :param agent_log_path: Where the Agent's stdout and stderr go inside the sandbox, quoted
        back when it fails to start.
    :param startup_timeout_seconds: How long to wait for a started Agent to answer ``/health``.
    :param extra_env: Further ``APP_SPARK_AGENT_*`` variables to hand the Agent. Model
        variables are refused, as for the local provider.
    """

    api_key: str = attrs.field(repr=False, validator=validate_non_empty_string)
    api_url: str = attrs.field(validator=validate_non_empty_string)
    callback_base_url: str = attrs.field(validator=validate_non_empty_string)
    domain: str | None = attrs.field(default=None, validator=attrs.validators.optional(validate_non_empty_string))
    template: str = attrs.field(default="e2b-python", validator=validate_non_empty_string)
    idle_timeout_seconds: int = attrs.field(default=1800, validator=attrs.validators.gt(0))
    max_lifetime_seconds: int = attrs.field(default=86400, validator=attrs.validators.gt(0))
    runtime_port: int = attrs.field(
        default=8000, validator=attrs.validators.and_(attrs.validators.ge(1), attrs.validators.le(65535))
    )
    preview_port: int = attrs.field(
        default=9000, validator=attrs.validators.and_(attrs.validators.ge(1), attrs.validators.le(65535))
    )
    port_scheme: Literal["http", "https"] = attrs.field(
        default="https", validator=attrs.validators.in_(("http", "https"))
    )
    workspace_dir: str = attrs.field(default="/data/workspace", validator=validate_sandbox_path)
    state_dir: str = attrs.field(default="/data/state")
    agent_command: str = attrs.field(default="python -m app_spark_agent", validator=validate_non_empty_string)
    agent_log_path: str = attrs.field(default="/tmp/app-spark-agent.log", validator=validate_sandbox_path)
    startup_timeout_seconds: float = attrs.field(default=60.0, validator=attrs.validators.gt(0))
    extra_env: dict[str, str] = attrs.field(factory=dict, validator=validate_agent_extra_env)

    @property
    def sandbox_timeout_seconds(self) -> int:
        """E2B deadline to set, counted from now, whenever a sandbox is created or renewed."""
        return self.idle_timeout_seconds + IDLE_EXIT_MARGIN_SECONDS

    @state_dir.validator
    def _validate_state_dir(self, attribute: attrs.Attribute[str], value: str) -> None:
        validate_sandbox_path(self, attribute, value)

        # 两个方向都要挡：state 在 workspace 里会被 agent 的文件工具改坏；workspace 在 state 里，
        # agent 写的文件就混进了会话历史。先规范化，`/data/workspace/../workspace/state` 这类写法
        # 才不会按字面绕过比较。
        workspace = PurePosixPath(posixpath.normpath(self.workspace_dir))
        state = PurePosixPath(posixpath.normpath(value))
        if state.is_relative_to(workspace) or workspace.is_relative_to(state):
            raise ValueError(f"{attribute.name} and workspace_dir must not contain each other")


@attrs.frozen
class StateCallback:
    """How a Runtime is told to write its state back to this service.

    :param path: Conversation-scoped public root, including FORCE_SCRIPT_NAME when the
        service is published under a sub-path. The Runtime appends its own channel names
        and never has to parse it. A provider that reaches this process without going
        through Ingress must strip the prefix; one that calls in through the public
        prefix must keep it.
    :param token: Bearer token authorizing writes to that one conversation.
    """

    path: str
    token: str


@attrs.frozen
class GitRemote:
    """How a Runtime is told to persist its workspace into the Project's repository.

    Sibling of :class:`StateCallback`, and passed the same way: the provider hands it to the
    process it starts and nothing else. A Runtime therefore learns one clone URL and one
    credential, and never has to know what a Project is or which one it is serving.

    Unlike the state token, this one is **not** revoked when the Runtime stops. It is long-lived
    and shared by every Runtime of the Project, so the defence against a replaced Runtime pushing
    stale history is the server refusing a non-fast-forward -- not taking the credential away.

    :param clone_url: The repository's HTTPS clone URL, as reachable *from the sandbox*. The
        control plane's own ``localhost`` is not that address.
    :param branch: The single working branch.
    :param username: HTTP Basic user, the service account that issued the token.
    :param token: Repository-scoped read-write token.
    """

    clone_url: str = attrs.field(validator=validate_non_empty_string)
    branch: str = attrs.field(validator=validate_non_empty_string)
    username: str = attrs.field(validator=validate_non_empty_string)
    token: str = attrs.field(repr=False, validator=validate_non_empty_string)


@attrs.frozen
class BkAidevModelConfig:
    """Defaults for a Runtime that calls bkaidev.

    The LLM base URL and the access_token exchange endpoint are not configured here: the former
    is built from BK_API_URL_TMPL and APIGW_ENVIRONMENT, the latter is TOKEN_AUTH_ENDPOINT. The
    app identity for the exchange is the service's own APP_CODE / APP_SECRET, never a nested copy.

    :param default_model_name: Model name injected as the Runtime's MODEL_NAME.
    """

    # agent 只在启动时按 MODEL_NAME 建一次模型，缺了就起不来可用的模型，所以这里必须有值。
    # 默认值要落在 agent 的 MODEL_PROFILES 里，表外的名字同样会让 Runtime 不可用。
    default_model_name: str = attrs.field(default="deepseek-v4-flash", validator=validate_non_empty_string)


@attrs.frozen
class DirectModelAccess:
    """What a Runtime is told to call a model vendor directly, with a fixed key.

    Also the shape of AGENT_DIRECT_MODEL_CONFIG: there is nothing to resolve per user.

    :param model: pydantic-ai model string, ``<provider>:<model>``, or ``fake:<scenario>``.
    :param api_key: The vendor key; omitted for ``fake:`` models.
    """

    model: str = attrs.field(validator=validate_non_empty_string)
    api_key: str | None = attrs.field(default=None, repr=False)


@attrs.frozen
class BkAidevModelAccess:
    """What a Runtime is told so it can call bkaidev on the user's behalf.

    Carries the access_token alone, no app credentials, so nothing in the sandbox can mint a
    token of its own.

    :param base_url: The gateway's OpenAI-compatible v1 root.
    :param access_token: The user's access_token for the configured app.
    :param model_name: The model the Runtime asks the gateway for.
    """

    base_url: str = attrs.field(validator=validate_non_empty_string)
    access_token: str = attrs.field(repr=False, validator=validate_non_empty_string)
    model_name: str = attrs.field(validator=validate_non_empty_string)


# Exactly one of the two, so a provider never has to guess what a missing value was meant to be.
type ModelAccess = DirectModelAccess | BkAidevModelAccess

# Called by a provider only when it is about to start a Runtime, inside whatever keeps two
# requests from starting rival Runtimes. Resolving any earlier would need a separate "is one
# already up" check, and the Runtime could die between that check and the start.
type ModelAccessResolver = Callable[[], Awaitable[ModelAccess]]


@attrs.frozen
class AgentRuntimeHandle:
    """Where a conversation's Runtime can be reached.

    Everything provider-specific stops here: both local and remote Runtimes are addressed by
    a URL, an Agent Bearer token, and any headers their transport needs. The client below does
    not need to know which provider produced the handle.

    :param conversation_id: Conversation this Runtime serves, one per process.
    :param base_url: Root URL the Runtime's HTTP API is served under.
    :param runtime_token: Bearer token required by every Runtime HTTP endpoint.
    :param http_headers: Additional transport headers required by the provider's port proxy.
    """

    conversation_id: str
    base_url: str
    runtime_token: str = attrs.field(repr=False, validator=validate_non_empty_string)
    http_headers: dict[str, str] = attrs.field(factory=dict, repr=False)


@attrs.frozen
class PreviewTarget:
    """Where a conversation's workspace application is proxied to, and how to reach it.

    :param base_url: Scheme-and-authority base URL of the application.
    :param http_headers: Transport headers the provider's port proxy requires, e.g. its access
        tokens. They authenticate this service to the proxy and never come from the browser.
    :param send_forwarded_host: Whether the application may be told the browser's host through
        ``X-Forwarded-Host``. A provider sets it to ``False`` when something between this
        service and the application routes by that header and rejects a foreign host.
    """

    base_url: str
    http_headers: dict[str, str] = attrs.field(factory=dict, repr=False)
    send_forwarded_host: bool = True


@attrs.frozen
class RuntimeHealth:
    """A Runtime's identity and the cursor of each of its three durable channels.

    :param model: Model the Runtime was configured with.
    :param conversation_id: Conversation bound to the Runtime, ``None`` before the first run.
    :param context_version: Version of the trusted context the next run will be given.
    :param log_seq: Last sequence number in the raw transcript.
    :param ui_event_seq: Last sequence number in the AG-UI event history.
    :param running: Whether a run currently occupies the Runtime.
    :param replication_pending: Whether the Runtime still holds state it has not managed to
        replicate. Distinct from ``running``: a flush that times out at the end of a turn hands
        the run guard back anyway, so an idle Runtime can still be ahead of this service.
    :param dev_server_status: What the Runtime says about the dev server hosting the workspace
        application -- ``not_started``, ``starting``, ``ready``, or ``stopped``. Forwarded rather
        than interpreted: this service has no opinion on the names, and an older Runtime that
        says nothing leaves it ``None``.
    """

    model: str
    conversation_id: str | None
    context_version: int
    log_seq: int
    ui_event_seq: int
    running: bool
    replication_pending: bool = False
    dev_server_status: str | None = None

    @classmethod
    def from_payload(cls, payload: Any) -> RuntimeHealth:
        """Build a health snapshot from a Runtime's ``/health`` body.

        :param payload: Decoded JSON body.
        :return: The parsed snapshot.
        :raises AgentUnavailableError: If the body is not the shape ``/health`` promises.
        """
        if not isinstance(payload, dict):
            raise AgentUnavailableError(f"Expected a JSON object from /health, got {payload!r}")
        try:
            return cls(
                model=str(payload["model"]),
                conversation_id=(None if payload["conversation_id"] is None else str(payload["conversation_id"])),
                context_version=int(payload["context_version"]),
                log_seq=int(payload["log_seq"]),
                ui_event_seq=int(payload["ui_event_seq"]),
                running=bool(payload["running"]),
                # Read leniently, unlike every field above it: a Runtime with no control plane
                # configured has no answer to give, and treating "did not say" as "nothing
                # pending" is the truthful reading of that.
                replication_pending=bool(payload.get("replication_pending", False)),
                # Lenient for a different reason: a Runtime that predates the field says
                # nothing, and "this Runtime cannot tell me" is not the same answer as any of
                # the four statuses it could have given.
                dev_server_status=(
                    None if payload.get("dev_server_status") is None else str(payload["dev_server_status"])
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AgentUnavailableError(f"Unreadable /health response: {exc}") from exc


@attrs.frozen
class EventPage:
    """One page of an Agent Runtime's append-only channel.

    :param since: Cursor the page was requested from.
    :param last_seq: Last sequence number the channel currently holds.
    :param records: The records themselves, forwarded as the Runtime wrote them.
    """

    since: int
    last_seq: int
    records: list[dict[str, Any]]

    @property
    def exhausted(self) -> bool:
        """Whether this page reached the end of the channel."""
        return not self.records or self.records[-1]["seq"] >= self.last_seq

    @classmethod
    def from_payload(cls, payload: Any) -> EventPage:
        """Build a page from a drain endpoint's body.

        :param payload: Decoded JSON body.
        :return: The parsed page.
        :raises AgentUnavailableError: If the body is not the shape the drain endpoints promise.
        """
        if not isinstance(payload, dict):
            raise AgentUnavailableError(f"Expected a JSON object from a drain, got {payload!r}")
        try:
            records = payload["records"]
            if not isinstance(records, list):
                raise TypeError(f"records must be a list, got {type(records).__name__}")
            return cls(
                since=int(payload["since"]),
                last_seq=int(payload["last_seq"]),
                records=records,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AgentUnavailableError(f"Unreadable drain response: {exc}") from exc


def structure_local_process_config(raw_config: object) -> LocalProcessConfig:
    """Structure and validate a local-process provider configuration.

    :param raw_config: Mapping from settings, typically loaded from YAML.
    :return: A validated configuration.
    :raises AgentConfigurationError: If the value has missing, extra, incorrectly typed, or
        otherwise invalid fields.
    """
    return structure_config(raw_config, LocalProcessConfig, error_cls=AgentConfigurationError)


def structure_e2b_config(raw_config: object) -> E2BConfig:
    """Structure and validate an E2B provider configuration.

    :param raw_config: Mapping from settings, typically loaded from YAML.
    :return: A validated configuration.
    :raises AgentConfigurationError: If the configuration is invalid.
    """
    return structure_config(raw_config, E2BConfig, error_cls=AgentConfigurationError)


def structure_bkaidev_model_config(raw_config: object) -> BkAidevModelConfig:
    """Structure and validate the bkaidev model configuration.

    :param raw_config: Mapping from settings, typically loaded from YAML.
    :return: A validated configuration.
    :raises ModelAccessConfigurationError: If the configuration is invalid.
    """
    return structure_config(raw_config, BkAidevModelConfig, error_cls=ModelAccessConfigurationError)


def structure_direct_model_config(raw_config: object) -> DirectModelAccess:
    """Structure and validate the direct model configuration.

    :param raw_config: Mapping from settings, typically loaded from YAML.
    :return: What every directly-calling Runtime is given.
    :raises ModelAccessConfigurationError: If the configuration is invalid.
    """
    return structure_config(raw_config, DirectModelAccess, error_cls=ModelAccessConfigurationError)
