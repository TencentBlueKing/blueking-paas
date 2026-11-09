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

"""控制面的启动入口：用户进入一个已有代码的项目时，把预览拉起来。

和模型的 launch_app（tools/launch_app.py）是同一个 AppSupervisor 的两个入口，共用一把锁、一个子进程、
同一条 app.launched。分成两个入口，是因为时机只有各自知道：模型知道代码刚改完，控制面知道用户刚进来。
两边要的也不一样：

- launch_app 走 restart：活着也停掉重拉，为的是加载新代码；控制面走 ensure_running，活着就不动——
  用户打开页面不是打断应用的理由。
- launch_app 等结果交回模型；这里不等，刚恢复的 workspace 没有 .venv，uv sync 可能要几分钟。
- launch_app 失败交回模型去改代码；这里没人接，失败只能记日志，体现为 dev_server_status 回落。
- launch_app 每轮限两次，防模型反复重试；这里不限，重复调用合并进进行中的那一次。
"""

import asyncio
import logging
from contextlib import suppress

from app_spark_agent.app_supervisor.supervisor import AppSupervisor

logger = logging.getLogger(__name__)


class PreviewStarter:
    """Start the workspace application in the background for the control plane, at most once at a time."""

    def __init__(self, supervisor: AppSupervisor) -> None:
        self._supervisor = supervisor

        # 留着引用：事件循环只弱引用任务，不留可能被回收；关停时也要靠它取消。
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Schedule ensure_running unless one is already scheduled, and return without waiting.

        :raises AppLaunchFailed: The workspace has no project.
        :raises AppLaunchConflict: A process the supervisor did not start owns the port.
        """

        # 不是协程：从判断到建任务之间不让出事件循环，两个并发请求就不会各建一个任务。
        if self._task is not None and not self._task.done():
            return

        # 能当场说清的失败当场说，免得调用方只能从状态回落去猜。
        self._supervisor.check_startable()
        self._task = asyncio.create_task(self._run())

    async def aclose(self) -> None:
        """Cancel a start still in progress. A child already spawned is stopped with the registry."""
        task = self._task
        if task is None or task.done():
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def _run(self) -> None:
        try:
            await self._supervisor.ensure_running()
        except Exception:
            # 没有调用方等着接这个异常。状态会回落到 not_started / stopped，原因在应用日志里。
            logger.warning("Starting the application for the control plane failed", exc_info=True)
