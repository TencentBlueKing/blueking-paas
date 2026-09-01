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

"""Where an Agent Runtime comes from."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app_spark_api.agent.runtime.entities import AgentRuntimeHandle, StateCallback


class AgentRuntimeProvider(abc.ABC):
    """Brings an Agent Runtime up for a conversation, and takes it down again.

    This is the seam the deployment story moves along. Today the only implementation spawns a
    process on this host; a sandbox implementation would replace it wholesale without anything
    above having to change, because both hand back the same
    :class:`~app_spark_api.agent.runtime.entities.AgentRuntimeHandle` and the Runtime behind it
    speaks the same HTTP either way.
    """

    @abc.abstractmethod
    async def ensure(
        self,
        *,
        project_id: str,
        conversation_id: str,
        state_callback: StateCallback | None = None,
    ) -> AgentRuntimeHandle:
        """Return a live Runtime for ``conversation_id``, starting one if needed.

        Only identity is passed in. Where the workspace and the durable state actually sit is
        the implementation's own business -- local directories here, something with no local
        path at all in a sandbox -- so deciding that is exactly what does not belong above this
        line.

        Implementations must be idempotent: a second call for a conversation that is already
        served has to return the running Runtime rather than start a rival one. A consequence
        worth stating: ``state_callback`` is only read when a Runtime is actually started, so a
        caller cannot use it to re-point a Runtime that is already up.

        :param project_id: Project being developed; its workspace is shared by every one of its
            conversations.
        :param conversation_id: Conversation the Runtime is bound to, one per Runtime.
        :param state_callback: Where the Runtime should replicate its durable state, and the
            token to do it with. Omitted for a Runtime that is to keep its state to itself.
        :return: Where the Runtime can be reached.
        :raises AgentProvisionError: If no Runtime could be brought up.
        :raises AgentWorkspaceBusyError: If another conversation of the same Project already
            holds a Runtime, which would put two agents in one workspace.
        """

    @abc.abstractmethod
    async def peek(self, conversation_id: str) -> AgentRuntimeHandle | None:
        """Return the Runtime already serving ``conversation_id``, without starting one.

        The counterpart to :meth:`ensure`, for the questions that must not cost a Runtime.
        Reporting whether a conversation has a run in flight is one; so is deciding whether a
        cold start needs its context injected. Answering those through ``ensure`` is what turns
        merely looking at a conversation into provisioning an agent for it.

        :param conversation_id: Conversation to look for.
        :return: Where the Runtime can be reached, or ``None`` if none is serving it.
        """

    @abc.abstractmethod
    async def terminate(self, conversation_id: str) -> None:
        """Shut down the Runtime serving ``conversation_id``, if there is one.

        Terminating an unknown conversation is not an error: callers clean up after failures
        they may not have caused.
        """

    @abc.abstractmethod
    async def shutdown(self) -> None:
        """Shut down every Runtime this provider is responsible for.

        For a service going down in an orderly way, and for tests that must not leak a Runtime
        into the next one.
        """
