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
from urllib.parse import urljoin

from app_spark_agent import settings


class AppStatus(StrEnum):
    """What health and launch report about the workspace application."""

    # 从未被本监督器 launch 过。别人占着端口也不算启动。
    NOT_STARTED = "not_started"

    # 已经 launch 过，但子进程掉了或约定端口没实听。
    UNHEALTHY = "unhealthy"

    # 本监督器的子进程还在，且约定端口 TCP 能连上。
    HEALTHY = "healthy"


# 请求没带 path/label 时用这两项；第一次 launch 和再次沿用都读这里。
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

# SIGTERM 之后等多久再 SIGKILL。
STOP_TIMEOUT_SECONDS = 5.0

# 重启前等旧端口放开。到期没等到也继续，由后面的实听等待收场。
PORT_FREE_TIMEOUT_SECONDS = 5.0

# skill 约定读这个键拿端口，不要让模型硬编码。
APP_PORT_ENV = f"{settings.ENV_PREFIX}APP_PORT"

# 只落盘给控制面 drain，不往进行中的 /runs SSE 里插。
LAUNCHED_EVENT_NAME = "app.launched"

# 子进程只剥这四个密钥。不要扩成全部 APP_SPARK_AGENT_*，那是模型 Shell 的名单。
SECRET_ENV_KEYS = (
    f"{settings.ENV_PREFIX}RUNTIME_TOKEN",
    f"{settings.ENV_PREFIX}MODEL_API_KEY",
    f"{settings.ENV_PREFIX}AIDEV_ACCESS_TOKEN",
    f"{settings.ENV_PREFIX}CONTROL_PLANE_TOKEN",
)


class AppLaunchError(Exception):
    """A launch the HTTP view maps to a status code."""


class AppLaunchConflict(AppLaunchError):
    """Another launch is in progress, or a foreign process owns the port."""


class AppLaunchInvalid(AppLaunchError):
    """path or label is not acceptable."""


class AppLaunchFailed(AppLaunchError):
    """The process did not start listening in time."""


@dataclass(frozen=True)
class LaunchResult:
    """What a successful launch hands back to the caller."""

    port: int
    path: str
    label: str
    url: str
    app_status: AppStatus

    def as_dict(self) -> dict[str, object]:
        """Return the JSON object POST /app/launch responds with."""
        return {
            "port": self.port,
            "path": self.path,
            "label": self.label,
            "url": self.url,
            "app_status": self.app_status,
        }


def validate_launch_path(path: str) -> str:
    """Accept a URL path that starts with / and names no host."""
    if not path.startswith("/") or path.startswith("//"):
        raise AppLaunchInvalid("path must be an absolute URL path starting with /.")
    if "://" in path or ".." in path:
        raise AppLaunchInvalid("path must not include a scheme or parent segments.")
    if any(ch.isspace() for ch in path):
        raise AppLaunchInvalid("path must not include whitespace.")
    return path


def validate_launch_label(label: str) -> str:
    """Accept a non-empty single-line label."""
    stripped = label.strip()
    if not stripped or len(stripped) > 64:
        raise AppLaunchInvalid("label must be between 1 and 64 characters.")
    if any(ch in stripped for ch in "\r\n"):
        raise AppLaunchInvalid("label must be a single line.")
    return stripped


def build_preview_url(path: str) -> str:
    """Join the preview base URL with path."""
    base = settings.preview_base_url().rstrip("/") + "/"
    if path == DEFAULT_LAUNCH_PATH:
        return base
    return urljoin(base, path.lstrip("/"))
