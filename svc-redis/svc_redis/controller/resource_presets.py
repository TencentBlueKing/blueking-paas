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

"""Redis 套餐资源规格
预定义 default / 1G / 2G 三档，CPU 统一 100m / 500m，内存 request 为 limit 的一半。
也支持自定义 requests 和 limits，或在 preset 上叠加，可见 README.md
"""

from copy import deepcopy
from typing import Dict, NamedTuple

from .entities import RedisPlanConfig, ResourcePresetName

# preset -> {requests, limits}，requests/limits 为任意 K8s 资源字典
RESOURCE_PRESETS: Dict[ResourcePresetName, Dict[str, Dict[str, str]]] = {
    "default": {
        "requests": {"cpu": "100m", "memory": "256Mi"},
        "limits": {"cpu": "500m", "memory": "512Mi"},
    },
    "1G": {
        "requests": {"cpu": "100m", "memory": "512Mi"},
        "limits": {"cpu": "500m", "memory": "1Gi"},
    },
    "2G": {
        "requests": {"cpu": "100m", "memory": "1Gi"},
        "limits": {"cpu": "500m", "memory": "2Gi"},
    },
}


class ResolvedResources(NamedTuple):
    requests: Dict[str, str]
    limits: Dict[str, str]


def resolve_plan_resources(plan_config: RedisPlanConfig) -> ResolvedResources:
    """解析套餐资源

    resources.preset 作为底稿，再叠加 resources.requests / limits。
    解析后 requests 与 limits 都必须有值，否则报错。
    """
    resources = plan_config.resources
    quota = _from_preset(resources.preset) if resources.preset else ResolvedResources({}, {})
    requests = {**quota.requests, **(resources.requests or {})}
    limits = {**quota.limits, **(resources.limits or {})}
    if not requests or not limits:
        raise ValueError("plan resources 必须提供完整的 requests 与 limits，或使用 preset")
    return ResolvedResources(requests=requests, limits=limits)


def _from_preset(preset: ResourcePresetName) -> ResolvedResources:
    spec = RESOURCE_PRESETS[preset]
    return ResolvedResources(requests=deepcopy(spec["requests"]), limits=deepcopy(spec["limits"]))
