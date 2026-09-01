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

"""Driving an Agent Runtime from this service.

Two abstractions, kept apart because they change for different reasons:

* :class:`~app_spark_api.agent.runtime.providers.base.AgentRuntimeProvider` decides *where* a
  Runtime lives and brings it up. Moving from a local process to a remote sandbox replaces this
  and nothing else.
* :class:`~app_spark_api.agent.runtime.client.AgentRuntimeClient` speaks the Runtime's HTTP
  contract. A sandboxed Runtime answers the same API, so this stays put.

Not a Django app: it owns no models, only the machinery for reaching a Runtime.
"""

from app_spark_api.agent.runtime.client import AgentRun, AgentRuntimeClient
from app_spark_api.agent.runtime.constants import AgentRuntimeProviderType
from app_spark_api.agent.runtime.entities import (
    AgentRuntimeHandle,
    EventPage,
    LocalProcessConfig,
    RuntimeHealth,
    StateCallback,
)
from app_spark_api.agent.runtime.exceptions import (
    AgentBusyError,
    AgentConfigurationError,
    AgentProvisionError,
    AgentRuntimeError,
    AgentUnavailableError,
    AgentWorkspaceBusyError,
)
from app_spark_api.agent.runtime.factory import (
    get_agent_runtime_provider,
    make_agent_runtime_provider,
)
from app_spark_api.agent.runtime.providers.base import AgentRuntimeProvider

__all__ = [
    "AgentBusyError",
    "AgentConfigurationError",
    "AgentProvisionError",
    "AgentRun",
    "AgentRuntimeClient",
    "AgentRuntimeError",
    "AgentRuntimeHandle",
    "AgentRuntimeProvider",
    "AgentRuntimeProviderType",
    "AgentUnavailableError",
    "AgentWorkspaceBusyError",
    "EventPage",
    "LocalProcessConfig",
    "RuntimeHealth",
    "StateCallback",
    "get_agent_runtime_provider",
    "make_agent_runtime_provider",
]
