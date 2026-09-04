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

"""Domain errors this package raises instead of leaking httpx or cattrs failures."""


class AgentRuntimeError(Exception):
    """Base class for every failure of the Agent Runtime integration."""


class AgentConfigurationError(AgentRuntimeError, ValueError):
    """The configured Agent Runtime provider or its settings are invalid."""


class AgentProvisionError(AgentRuntimeError):
    """An Agent Runtime could not be brought up for a conversation."""


class AgentWorkspaceBusyError(AgentRuntimeError):
    """Another conversation already holds a live Runtime on the same workspace.

    A workspace belongs to a Project while a Runtime belongs to a conversation, so two
    conversations of one Project would otherwise have two agents editing the same files.
    """


class AgentUnavailableError(AgentRuntimeError):
    """The Agent Runtime could not be reached, or answered in a way it never should."""


class AgentBusyError(AgentRuntimeError):
    """The Agent Runtime is already executing a run for this conversation."""
