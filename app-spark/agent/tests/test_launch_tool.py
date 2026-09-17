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

"""模型侧 launch 工具：失败折成结构体、单轮封顶、下一轮重新给额度。"""

from typing import cast

import pytest

from app_spark_agent.app_supervisor import (
    AppLaunchConflict,
    AppLaunchFailed,
    AppStatus,
    AppSupervisor,
    LaunchResult,
)
from app_spark_agent.launch_tool import MAX_LAUNCHES_PER_RUN, LaunchTool

URL = "http://127.0.0.1:8000/"


def launched(url: str = URL) -> LaunchResult:
    return LaunchResult(port=8000, path="/", label="Preview", url=url, app_status=AppStatus.HEALTHY)


class StubSupervisor:
    """按脚本成功或抛，并记录真正被发起了几次。"""

    def __init__(self, *outcomes: LaunchResult | Exception) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0

    async def launch(self, path: str | None = None, label: str | None = None) -> LaunchResult:
        self.calls += 1
        outcome = self._outcomes.pop(0) if self._outcomes else launched()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make_tool(*outcomes: LaunchResult | Exception) -> tuple[LaunchTool, StubSupervisor]:
    stub = StubSupervisor(*outcomes)
    return LaunchTool(cast(AppSupervisor, stub)), stub


async def test_a_listening_app_hands_back_its_url() -> None:
    tool, stub = make_tool(launched("http://preview.example.com/"))

    result = await tool.launch()

    assert result.status == "ok"
    assert result.url == "http://preview.example.com/"
    assert stub.calls == 1


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(AppLaunchFailed("The application did not listen before the deadline."), id="did-not-listen"),
        pytest.param(AppLaunchConflict("An application launch is already in progress."), id="control-plane-launching"),
    ],
)
async def test_a_failure_is_reported_rather_than_raised(error: Exception) -> None:
    """抛出去会中断整轮；模型本可以读日志、改代码再试一次。"""
    tool, _ = make_tool(error)

    result = await tool.launch()

    assert result.status == "failed"
    assert result.detail == str(error)
    assert result.url == ""


async def test_the_budget_runs_out_within_one_run() -> None:
    tool, stub = make_tool(*[AppLaunchFailed("nope")] * MAX_LAUNCHES_PER_RUN)

    for _ in range(MAX_LAUNCHES_PER_RUN):
        assert (await tool.launch()).status == "failed"
    refused = await tool.launch()

    assert refused.status == "refused"
    # 被拒的那次不该再打到监督器上。
    assert stub.calls == MAX_LAUNCHES_PER_RUN


async def test_the_next_run_is_given_a_fresh_budget() -> None:
    tool, stub = make_tool(*[AppLaunchFailed("nope")] * MAX_LAUNCHES_PER_RUN)
    for _ in range(MAX_LAUNCHES_PER_RUN):
        await tool.launch()
    assert (await tool.launch()).status == "refused"

    tool.begin_run()

    assert (await tool.launch()).status == "ok"
    assert stub.calls == MAX_LAUNCHES_PER_RUN + 1
