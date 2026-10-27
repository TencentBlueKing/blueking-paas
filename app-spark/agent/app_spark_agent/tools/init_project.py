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

"""模型侧的 init_project：真要开始写代码时，由模型自己从模板建出 Python 项目。

只是 AppArchitecture.init_project 的薄适配：为什么由程序而不是模型写文件内容，见 app_arch/python.py；
建项目与同步平台配置的分工，见 app_arch/architecture.py。
"""

from collections.abc import Callable
from pathlib import Path

from app_spark_agent.app_arch.architecture import AppArchitecture
from app_spark_agent.app_arch.files import FileSyncResult


def build_init_project_tool(workspace: Path) -> Callable[[str], FileSyncResult]:
    """Return the init_project tool bound to workspace, as the plain function the harness registers.

    Name and docstring are what the model sees. The function blocks on file writes, which the
    harness runs in a worker thread for a synchronous tool.
    """
    architecture = AppArchitecture(workspace)

    def init_project(name: str) -> FileSyncResult:
        """Create the Python project for this app from the platform's template.

        Call this once, before writing the application's first file. It writes `pyproject.toml`
        and `uv.lock` with the starting dependencies already locked, plus the platform-owned
        `app_desc.yaml` and `.python-version` files required for deployment.
        When `pyproject.toml` already exists it keeps the project files as they are and only
        repairs the platform files; a `uv.lock` left without one is replaced.

        :param name: A short name for the app in lowercase ASCII letters, digits and hyphens,
            for example `todo-board`. Spaces, underscores and dots become hyphens.
        """
        return architecture.init_project(name)

    return init_project
