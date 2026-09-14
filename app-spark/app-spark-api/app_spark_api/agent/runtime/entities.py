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

from typing import Any

import attrs

from app_spark_api.agent.runtime.exceptions import AgentConfigurationError, AgentUnavailableError
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
    :param model: Value for ``APP_SPARK_AGENT_MODEL``; left to the agent's default when unset.
    :param model_api_key: Value for ``APP_SPARK_AGENT_MODEL_API_KEY``; left to the agent's
        default when unset.
    :param startup_timeout_seconds: How long to wait for a spawned Runtime to answer
        ``/health``.
    :param extra_env: Further ``APP_SPARK_AGENT_*`` variables to hand the process, so an agent
        setting can be reached without growing a field here for each one.
    """

    agent_project_dir: str = attrs.field(validator=validate_non_empty_string)
    workspace_root: str = attrs.field(validator=validate_non_empty_string)
    state_root: str = attrs.field(validator=validate_non_empty_string)
    callback_base_url: str = "http://127.0.0.1:8000"
    model: str | None = None
    model_api_key: str | None = None
    startup_timeout_seconds: float = 60.0
    extra_env: dict[str, str] = attrs.field(factory=dict)


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
class AgentRuntimeHandle:
    """Where a conversation's Runtime can be reached.

    Everything provider-specific stops here: a Runtime in a remote sandbox is addressed by the
    same base URL as one spawned locally, which is why the client below never learns which
    provider produced it.

    :param conversation_id: Conversation this Runtime serves, one per process.
    :param base_url: Root URL the Runtime's HTTP API is served under.
    :param runtime_token: Bearer token required by every Runtime HTTP endpoint.
    """

    conversation_id: str
    base_url: str
    runtime_token: str = attrs.field(repr=False, validator=validate_non_empty_string)


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
    """

    model: str
    conversation_id: str | None
    context_version: int
    log_seq: int
    ui_event_seq: int
    running: bool
    replication_pending: bool = False

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
