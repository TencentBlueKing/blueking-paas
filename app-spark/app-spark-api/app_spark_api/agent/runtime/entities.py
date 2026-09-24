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

from collections.abc import Awaitable, Callable
from typing import Any, Literal

import attrs

from app_spark_api.agent.runtime.constants import ENV_PREFIX, MODEL_ENV_NAMES
from app_spark_api.agent.runtime.exceptions import (
    AgentConfigurationError,
    AgentUnavailableError,
    ModelAccessConfigurationError,
)

# cattrs resolves BkAidevModelConfig.token's annotation at runtime to structure it.
from app_spark_api.infras.bk_access_token import AccessTokenClientConfig  # noqa: TC001
from app_spark_api.utils import structure_config, validate_non_empty_string


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
    extra_env: dict[str, str] = attrs.field(factory=dict)

    @extra_env.validator
    def _validate_extra_env(self, attribute: attrs.Attribute[dict[str, str]], value: dict[str, str]) -> None:
        # 只放行 agent 自己的配置：本服务的其它变量（尤其是 APP_SPARK_API_* 里的平台密钥）不能借
        # 这个口子流进 Runtime。
        foreign = sorted(name for name in value if not name.startswith(ENV_PREFIX))
        if foreign:
            raise ValueError(f"{attribute.name} may only hold {ENV_PREFIX}* variables, got {foreign}")

        owned = sorted(MODEL_ENV_NAMES.intersection(value))
        if owned:
            raise ValueError(f"{attribute.name} must not set model variables, use the model source settings: {owned}")


@attrs.frozen
class E2BConfig:
    """Configuration for provisioning an E2B sandbox per conversation.

    :param api_key: Credential for the E2B-compatible API.
    :param api_url: Base URL of that API; independent of the exposed port domain.
    :param domain: Fallback domain for sandbox hosts when the API does not return one.
    :param template: Sandbox template name or ID.
    :param timeout_seconds: E2B sandbox time to live in seconds from creation (default 3600).
        Activity and this provider's reconnects do not renew it; E2B stops the sandbox when
        the timeout expires unless its deadline is explicitly extended.
    :param runtime_port: Port reserved for the future Agent Runtime HTTP server.
    :param preview_port: Fixed sandbox port for the workspace application preview.
    :param port_scheme: URL scheme for the exposed port proxy.
    """

    api_key: str = attrs.field(repr=False, validator=validate_non_empty_string)
    api_url: str = attrs.field(validator=validate_non_empty_string)
    domain: str | None = attrs.field(default=None, validator=attrs.validators.optional(validate_non_empty_string))
    template: str = attrs.field(default="e2b-python", validator=validate_non_empty_string)
    timeout_seconds: int = attrs.field(default=3600, validator=attrs.validators.gt(0))
    runtime_port: int = attrs.field(
        default=8000, validator=attrs.validators.and_(attrs.validators.ge(1), attrs.validators.le(65535))
    )
    preview_port: int = attrs.field(
        default=9000, validator=attrs.validators.and_(attrs.validators.ge(1), attrs.validators.le(65535))
    )
    port_scheme: Literal["http", "https"] = attrs.field(
        default="https", validator=attrs.validators.in_(("http", "https"))
    )


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
    """How Agent Runtimes reach bkaidev's LLM gateway, and how their access_token is obtained.

    :param base_url: The gateway's OpenAI-compatible v1 root, without ``/chat/completions``.
    :param model_name: Model to call. Must be one the app has been granted on bkaidev, and one
        the agent's MODEL_PROFILES lists, or the Runtime starts with its model not ready.
    :param token: The app identity and token service the user's access_token is exchanged at.
        Its app_secret is used for the exchange only and never reaches a Runtime.
    """

    base_url: str = attrs.field(validator=validate_non_empty_string)
    model_name: str = attrs.field(validator=validate_non_empty_string)
    token: AccessTokenClientConfig


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
    :param model_name: Model to call.
    :param access_token: The user's access_token for the configured app.
    """

    base_url: str = attrs.field(validator=validate_non_empty_string)
    model_name: str = attrs.field(validator=validate_non_empty_string)
    access_token: str = attrs.field(repr=False, validator=validate_non_empty_string)


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
