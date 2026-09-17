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

"""模型侧的 launch：进程内直调监督器，不走 HTTP、不碰任何凭据。

只有 agent 第一时间知道代码什么时候真的能跑，所以拉起这件事不该只等用户点按钮。
控制面那条 POST /app/launch 仍然保留：两条路径共用同一把锁、同一份 LaunchResult，
成功都落同一条 app.launched 到 ui_events，控制面照旧 drain，不需要反向回调。
"""

from typing import Literal

from pydantic import BaseModel

from app_spark_agent.app_supervisor import AppLaunchError, AppSupervisor

# 单轮上限。launch 失败后模型会倾向于「改代码再 launch」，不封顶就会一直烧 token。
# 一次首发加一次修好够用了；还不行就把原因交回用户，别再自己试。
MAX_LAUNCHES_PER_RUN = 2

REFUSED_DETAIL = f"Already launched {MAX_LAUNCHES_PER_RUN} times in this turn. Report the failure instead of retrying."


class LaunchToolResult(BaseModel):
    """launch 工具返回给模型的结构，方便按字段消费而不是猜一段纯文本。

    :param status: ok 端口已实听；failed 没起来；refused 本轮次数已用尽。
    :param url: 成功时可以打开的地址。
    :param detail: 失败或被拒的原因。
    """

    status: Literal["ok", "failed", "refused"]
    url: str = ""
    detail: str = ""


class LaunchTool:
    """Launch the workspace application for the model, a bounded number of times per run."""

    def __init__(self, supervisor: AppSupervisor, *, max_per_run: int = MAX_LAUNCHES_PER_RUN) -> None:
        self._supervisor = supervisor
        self._max_per_run = max_per_run
        self._used = 0

    def begin_run(self) -> None:
        """Reset the per-run budget. POST /runs calls this before the model starts."""

        # 按轮清零，不按会话：额度是防一轮里反复重试，不是给整个会话设总量。
        self._used = 0

    async def launch(self) -> LaunchToolResult:
        """Start or restart the application and report something the model can act on."""
        if self._used >= self._max_per_run:
            return LaunchToolResult(status="refused", detail=REFUSED_DETAIL)

        # 先计数：被拒的那次不算，真正发起了就算，哪怕接下来失败。
        self._used += 1
        try:
            result = await self._supervisor.launch()
        except AppLaunchError as exc:
            # 不往上抛。抛出去会中断整轮，而模型本可以读日志、改代码再试一次。
            return LaunchToolResult(status="failed", detail=str(exc))

        return LaunchToolResult(status="ok", url=result.url)
