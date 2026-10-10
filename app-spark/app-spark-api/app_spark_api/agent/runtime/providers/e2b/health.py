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

"""Ask a sandbox Agent whether it is up, and build the headers its port proxy requires."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app_spark_api.agent.runtime.client import AgentRuntimeClient
from app_spark_api.agent.runtime.exceptions import AgentUnavailableError

from . import constants

if TYPE_CHECKING:
    from e2b import AsyncSandbox

    from app_spark_api.agent.runtime.entities import AgentRuntimeHandle, RuntimeHealth


async def read_agent_health(
    handle: AgentRuntimeHandle, *, timeout_seconds: float = constants.HEALTH_PROBE_TIMEOUT_SECONDS
) -> RuntimeHealth | None:
    """Read the Runtime's /health behind handle, or None if it does not answer.

    :param handle: Where the Runtime should be reachable.
    :param timeout_seconds: Upper bound on this one probe.
    :return: Its health snapshot, or None if it gave no usable one.
    """
    try:
        return await AgentRuntimeClient(handle, timeout_seconds=timeout_seconds).health()
    except AgentUnavailableError:
        return None


async def probe_agent_health(
    handle: AgentRuntimeHandle, *, timeout_seconds: float = constants.HEALTH_PROBE_TIMEOUT_SECONDS
) -> bool:
    """Tell whether the Runtime behind ``handle`` answers ``/health`` yet.

    :param handle: Where the Runtime should be reachable.
    :param timeout_seconds: Upper bound on this one probe.
    :return: Whether it answered with a usable health snapshot.
    """
    return await read_agent_health(handle, timeout_seconds=timeout_seconds) is not None


def port_headers(sandbox: AsyncSandbox) -> dict[str, str]:
    """Forward tokens required by the E2B proxy for an exposed application port."""
    headers: dict[str, str] = {}
    # The self-hosted proxy in front of our E2B service requires the same sandbox access
    # token the SDK sends to envd. Read it through the SDK's public connection config, not
    # through the sandbox's private token field. The port itself comes from get_host().
    if access_token := sandbox.connection_config.sandbox_headers.get("X-Access-Token"):
        headers["X-Access-Token"] = access_token
    if sandbox.traffic_access_token:
        headers["E2B-Traffic-Access-Token"] = sandbox.traffic_access_token
    return headers
