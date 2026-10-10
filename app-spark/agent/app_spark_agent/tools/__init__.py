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

"""The platform's own tools for the model, one module per tool, named after the tool it registers.

FileSystem 与 Shell 来自 harness，不在这里。这里的每个工具都把函数名和 docstring 当成模型看到的
名字和说明，返回一个 pydantic 结构而不是一段纯文本；settings.INSTRUCTIONS 按名字提到它们，
改名时两处一起改。

- read_app_log.py：只读本会话的应用日志，路径不是参数；
- init_project.py：真要开始写代码时，从模板建出 Python 项目；
- launch_app.py：拉起或重启应用，单轮有次数上限。它有按轮的状态，归 ConversationRuntime 持有，
  由 create_agent 的 extra_tools 交进来，另外两个由 create_agent 自己绑定 workspace 建出。
"""

from app_spark_agent.tools.init_project import InitProjectResult, ProjectInitializer, build_init_project_tool
from app_spark_agent.tools.launch_app import MAX_LAUNCHES_PER_RUN, LaunchTool, LaunchToolResult
from app_spark_agent.tools.read_app_log import AppLogReader, AppLogReadResult, build_read_app_log_tool

__all__ = [
    "MAX_LAUNCHES_PER_RUN",
    "AppLogReadResult",
    "AppLogReader",
    "InitProjectResult",
    "LaunchTool",
    "LaunchToolResult",
    "ProjectInitializer",
    "build_init_project_tool",
    "build_read_app_log_tool",
]
