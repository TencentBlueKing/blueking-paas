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

"""Launch errors, status names, and path or label checks."""

from dataclasses import dataclass
from enum import StrEnum

from app_spark_agent import settings


class AppStatus(StrEnum):
    """What health and launch report about the workspace application."""

    # 从未被本监督器 launch 过。别人占着端口也不算启动。
    NOT_STARTED = "not_started"

    # 已经 launch 过，但子进程掉了或约定端口答不出 HTTP。
    UNHEALTHY = "unhealthy"

    # 本监督器的子进程还在，且约定端口应答得了一个 HTTP GET。
    HEALTHY = "healthy"


# 应用把自己摆在哪个路径下，以及给人看的标签。写进 app.launched 供前端用。
#
# 是常量而不是入参：能传别的值的调用方只有当初那个控制面 launch 接口，它已经没了。模型的
# launch_app 不接受参数，于是「可配的 path」是一条不存在的路径——留着会让人以为它能变。
DEFAULT_LAUNCH_PATH = "/"
DEFAULT_LAUNCH_LABEL = "Preview"

# 手动 launch 最多等这么久听到端口。超时停掉半活子进程，避免留下占着环境的进程。
LISTEN_TIMEOUT_SECONDS = 30.0

# 从上次手动 launch 起算。成功也不清零，避免听上又立刻崩时无限重启。
CRASH_RETRY_LIMIT = 3

# 掉听后先睡再拉，避免进程刚退出就立刻 spawn。
CRASH_RETRY_INTERVAL_SECONDS = 2.0

# watch 轮询间隔。掉听另有上面的缓冲，不必更密。
CRASH_WATCH_POLL_SECONDS = 0.5

# 重启前等旧端口放开。到期没等到也继续，由后面的实听等待收场。
PORT_FREE_TIMEOUT_SECONDS = 5.0

# 注入给子进程的端口。应用不靠它选端口，监听端口由启动命令决定。
APP_PORT_ENV = f"{settings.ENV_PREFIX}APP_PORT"

# 只落盘给控制面 drain，不往进行中的 /runs SSE 里插。
LAUNCHED_EVENT_NAME = "app.launched"

# 控制面签发真实 run_id。这里用固定哨兵，避免每次 launch 灌一个 uuid 进 AppendLog._run_ids。
LAUNCH_EVENT_RUN_ID = "app-supervisor"


class AppLaunchError(Exception):
    """A launch the tool reports as failed, without aborting the run."""


class AppLaunchConflict(AppLaunchError):
    """Another launch is in progress, or a foreign process owns the port."""


class AppLaunchFailed(AppLaunchError):
    """The process did not start listening in time."""


@dataclass(frozen=True)
class LaunchResult:
    """What a successful launch hands back to the caller."""

    # 没有 url：沙箱里没人知道浏览器该打开哪个地址，那是控制面签发的。这里只说端口在听，
    # 以及应用把自己摆在哪个路径下。
    port: int
    path: str
    label: str
    app_status: AppStatus
