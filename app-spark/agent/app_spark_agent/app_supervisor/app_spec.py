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

"""How the workspace application is started: the command, the environment, the log file."""

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from app_spark_agent import settings
from app_spark_agent.app_supervisor.process import ProcessSpec
from app_spark_agent.app_supervisor.types import APP_PORT_ENV, SECRET_ENV_KEYS

# 模型被要求把应用导出成这个路径，启动方也只启这一个。settings.INSTRUCTIONS 里写着同一条
# 约定，两处要一起改：模型写成别的入口名，launch 一定失败。
APP_IMPORT_PATH = "main:app"

# 听所有网卡，给沙箱外的预览代理访问。判活仍只连 127.0.0.1。
APP_LISTEN_HOST = "0.0.0.0"


def build_app_spec(workspace: Path, port: int) -> ProcessSpec:
    """Describe the uvicorn child that serves the workspace application."""
    return ProcessSpec(
        # 用本进程的 Python，确保跑的是装了 uvicorn 的那个解释器。
        argv=(
            sys.executable,
            "-m",
            "uvicorn",
            APP_IMPORT_PATH,
            "--host",
            APP_LISTEN_HOST,
            "--port",
            str(port),
        ),
        cwd=workspace,
        env=build_child_environ(port),
        log_path=Path(settings.APP_LOG_PATH),
    )


def build_child_environ(port: int, source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Copy the parent environment, inject the app port, and drop secrets."""
    env = dict(os.environ if source is None else source)
    for key in SECRET_ENV_KEYS:
        env.pop(key, None)

    # 应用自己不选端口，注入只为让代码里需要时能读到同一个值。
    env[APP_PORT_ENV] = str(port)
    return env
