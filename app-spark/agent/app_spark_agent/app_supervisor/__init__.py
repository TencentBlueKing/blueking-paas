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

"""Start and restart the workspace application so a caller can open it over HTTP.

分三层：process.py 是通用子进程托管，app_spec.py 说清这个应用怎么启，supervisor.py 只管
策略（一次一个 launch、掉听重启额度、状态、事件）。
"""

from app_spark_agent.app_supervisor.app_spec import build_app_spec, build_child_environ
from app_spark_agent.app_supervisor.process import ManagedProcess, ProcessRegistry, ProcessSpec
from app_spark_agent.app_supervisor.supervisor import AppSupervisor
from app_spark_agent.app_supervisor.types import (
    APP_PORT_ENV,
    LAUNCH_EVENT_RUN_ID,
    LAUNCHED_EVENT_NAME,
    AppLaunchConflict,
    AppLaunchError,
    AppLaunchFailed,
    AppLaunchInvalid,
    AppStatus,
    LaunchResult,
    validate_launch_label,
    validate_launch_path,
)

__all__ = [
    "APP_PORT_ENV",
    "LAUNCHED_EVENT_NAME",
    "LAUNCH_EVENT_RUN_ID",
    "AppLaunchConflict",
    "AppLaunchError",
    "AppLaunchFailed",
    "AppLaunchInvalid",
    "AppStatus",
    "AppSupervisor",
    "LaunchResult",
    "ManagedProcess",
    "ProcessRegistry",
    "ProcessSpec",
    "build_app_spec",
    "build_child_environ",
    "validate_launch_label",
    "validate_launch_path",
]
