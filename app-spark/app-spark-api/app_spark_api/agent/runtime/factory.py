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

"""Building the configured Agent Runtime provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver

from app_spark_api.agent.runtime.constants import AgentRuntimeProviderType
from app_spark_api.agent.runtime.entities import structure_local_process_config
from app_spark_api.agent.runtime.exceptions import AgentConfigurationError
from app_spark_api.agent.runtime.providers.local import LocalProcessProvider

if TYPE_CHECKING:
    from app_spark_api.agent.runtime.providers.base import AgentRuntimeProvider

_provider: AgentRuntimeProvider | None = None


def make_agent_runtime_provider(provider: str, config: object) -> AgentRuntimeProvider:
    """Build an Agent Runtime provider from its name and configuration.

    Example::

        provider = make_agent_runtime_provider(
            AgentRuntimeProviderType.LOCAL_PROCESS,
            {
                "agent_project_dir": "/srv/app-spark/agent",
                "workspace_root": "/var/lib/app-spark/workspaces",
                "state_root": "/var/lib/app-spark/agent-state",
            },
        )

    :param provider: A value from :class:`AgentRuntimeProviderType`.
    :param config: Provider-specific configuration mapping.
    :return: A validated provider.
    :raises AgentConfigurationError: If the provider is unknown or its configuration cannot be
        structured.
    """
    try:
        provider_type = AgentRuntimeProviderType(provider)
    except ValueError as exc:
        raise AgentConfigurationError(f"Unknown Agent Runtime provider: {provider}") from exc

    if provider_type == AgentRuntimeProviderType.LOCAL_PROCESS:
        return LocalProcessProvider(structure_local_process_config(config))

    raise AgentConfigurationError(f"Unsupported Agent Runtime provider: {provider_type}")


def get_agent_runtime_provider() -> AgentRuntimeProvider:
    """Return the provider this service drives its agents through.

    Cached for the life of the process because the local provider owns the child processes it
    started: rebuilding it per request would lose track of every running Runtime.

    :return: The configured provider.
    :raises AgentConfigurationError: If the settings do not describe a usable provider.
    """
    global _provider
    if _provider is None:
        _provider = make_agent_runtime_provider(
            settings.AGENT_RUNTIME_PROVIDER,
            settings.AGENT_RUNTIME_PROVIDER_CONFIG,
        )
    return _provider


@receiver(setting_changed)
def _reset_provider(*, setting: str, **kwargs: object) -> None:
    """Drop the cached provider when a test overrides the settings it was built from.

    Any Runtime the discarded provider still had running is left to the ``atexit`` hook in
    :mod:`~app_spark_api.agent.runtime.providers.local`, since this signal is synchronous and
    stopping them is not. Tests that spawn Runtimes should shut their provider down themselves.
    """
    if setting in {"AGENT_RUNTIME_PROVIDER", "AGENT_RUNTIME_PROVIDER_CONFIG"}:
        global _provider
        _provider = None
