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

"""Renew an E2B sandbox deadline, and tell when a sandbox is too old to reuse."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone
from e2b import AsyncSandbox

from app_spark_api.agent.runtime.models import E2BSandboxRecord

from . import constants

if TYPE_CHECKING:
    from app_spark_api.agent.runtime.entities import E2BConfig

logger = logging.getLogger(__name__)


class SandboxLifetime:
    """The E2B deadline of one provider's sandboxes, and the age after which one is replaced."""

    def __init__(self, config: E2BConfig) -> None:
        self.config = config

    async def extend(self, conversation_id: str) -> None:
        """Renew the sandbox still serving this conversation, if one is active.

        :param conversation_id: Conversation whose turn is running or just ended.
        """
        # 只取 sandbox_id。整行会把 runtime_token 这些加密字段解密出来，续期用不到。
        # 活跃会话没有了（本轮中途被结束、沙箱已回收）就跳过，不续一个已经交还的沙箱。
        sandbox_id = await (
            E2BSandboxRecord.objects.active_for_conversation(conversation_id)
            .values_list("sandbox_id", flat=True)
            .afirst()
        )
        await self.renew(sandbox_id)

    async def renew(self, sandbox_id: str | None) -> None:
        """Set this sandbox to expire sandbox_timeout_seconds from now, best effort.

        :param sandbox_id: Sandbox to renew. Nothing is done when the claim has not been bound yet.
        """
        if sandbox_id is None:
            return

        # 续期失败只记告警：对话本身不受影响，最坏是沙箱按上一次的存活期提前到期、下一轮重建。
        # 限时：它挡在一轮的开头和结尾，控制面卡住时不能让这一轮跟着等上 SDK 默认的 60 秒。
        # 不只接 SandboxException：控制面的网络错误不一定被 SDK 包成它。
        try:
            async with asyncio.timeout(constants.RENEW_TIMEOUT_SECONDS):
                await AsyncSandbox.set_timeout(
                    sandbox_id,
                    self.config.sandbox_timeout_seconds,
                    api_key=self.config.api_key,
                    api_url=self.config.api_url,
                    domain=self.config.domain,
                    request_timeout=constants.RENEW_TIMEOUT_SECONDS,
                )
        except Exception:
            logger.warning("Could not extend the lifetime of E2B sandbox %s", sandbox_id, exc_info=True)

    def is_past(self, record: E2BSandboxRecord) -> bool:
        """Whether this claim was made at least max_lifetime_seconds ago."""
        deadline = record.created_at + timedelta(seconds=self.config.max_lifetime_seconds)
        return timezone.now() >= deadline
