# -*- coding: utf-8 -*-
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

"""Agent Sandbox 视图

用户态接口见 `api`, 应用态 (系统 API) 接口见 `sys_api`;
此处统一导出, 使 `urls.py` 等调用方保持 `views.XxxViewSet` 的引用方式不变。
"""

from .api import (
    AgentSandboxFSViewSet,
    AgentSandboxProcessViewSet,
    AgentSandboxViewSet,
    VolumeFileViewSet,
    VolumeViewSet,
)
from .sys_api import SysAgentSandboxAPIPermissionViewSet

__all__ = [
    "AgentSandboxFSViewSet",
    "AgentSandboxProcessViewSet",
    "AgentSandboxViewSet",
    "SysAgentSandboxAPIPermissionViewSet",
    "VolumeFileViewSet",
    "VolumeViewSet",
]
