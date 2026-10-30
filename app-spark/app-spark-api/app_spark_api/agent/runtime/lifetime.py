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

"""Renewing a Runtime's idle deadline from code that must not fail because of it."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from app_spark_api.agent.runtime.providers.base import AgentRuntimeProvider

logger = logging.getLogger(__name__)


async def extend_lifetime_quietly(provider: AgentRuntimeProvider, conversation_id: UUID) -> None:
    """Count a turn as activity for the conversation's Runtime, never failing.

    Both callers are already past the point where a failure could be reported: one is closing a
    stream the client may have left, the other has stored a batch the Runtime must not re-send.
    The worst a missed renewal does is let the Runtime expire sooner.

    Shielded, because both callers can be cancelled by their client going away -- a stream by the
    browser, a state write-back by the Runtime's own timeout -- and the renewal is owed either way.

    :param provider: The provider serving the conversation; passed in so callers keep owning which
        one that is.
    :param conversation_id: Conversation whose Runtime was just used.
    """
    try:
        await asyncio.shield(provider.extend_lifetime(str(conversation_id)))
    except Exception:
        logger.warning(
            "Could not extend the Agent Runtime lifetime of conversation %s", conversation_id, exc_info=True
        )
