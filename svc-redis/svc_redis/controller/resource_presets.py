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
预定义了几组规格，因为 redis 几乎不吃 cpu，所以 cpu 的配额比较低
同时也支持自定义 requests 和 limits
也支持二者组合使用，可见 README.md
"""

from copy import deepcopy
from typing import Dict, NamedTuple

from kubernetes.utils.quantity import parse_quantity

from .entities import RedisPlanConfig, ResourcePresetName

DEFAULT_RESOURCE_PRESET: ResourcePresetName = "micro"

# preset -> {requests, limits}，requests/limits 为任意 K8s 资源字典
RESOURCE_PRESETS: Dict[ResourcePresetName, Dict[str, Dict[str, str]]] = {
    "nano": {
        "requests": {"cpu": "50m", "memory": "128Mi"},
        "limits": {"cpu": "500m", "memory": "256Mi"},
    },
    "micro": {
        "requests": {"cpu": "50m", "memory": "256Mi"},
        "limits": {"cpu": "500m", "memory": "512Mi"},
    },
    "small": {
        "requests": {"cpu": "50m", "memory": "512Mi"},
        "limits": {"cpu": "500m", "memory": "1024Mi"},
    },
    "medium": {
        "requests": {"cpu": "100m", "memory": "1024Mi"},
        "limits": {"cpu": "1", "memory": "2048Mi"},
    },
}


class ResolvedResources(NamedTuple):
    requests: Dict[str, str]
    limits: Dict[str, str]


def resolve_plan_resources(plan_config: RedisPlanConfig) -> ResolvedResources:
    """解析套餐资源

    优先级：
    1. resources.preset 作为底稿，再叠加 resources.requests / limits
    2. requests/limits 只配了一个时，缺的一侧复用另一侧
    3. 未配 resources 时：若配了 memory_size 走历史配额计算方式，否则用默认 preset
    """
    resources = plan_config.resources
    if resources is None:
        if plan_config.memory_size:
            return _from_memory_size(plan_config.memory_size)
        return _from_preset(DEFAULT_RESOURCE_PRESET)

    quota = _from_preset(resources.preset) if resources.preset else ResolvedResources({}, {})
    # 可覆盖 preset 的配额
    requests = {**quota.requests, **(resources.requests or {})}
    limits = {**quota.limits, **(resources.limits or {})}

    if not requests and not limits:
        return _from_preset(DEFAULT_RESOURCE_PRESET)
    if not requests:
        requests = dict(limits)
    if not limits:
        limits = dict(requests)
    return ResolvedResources(requests=requests, limits=limits)


def _from_preset(preset: ResourcePresetName) -> ResolvedResources:
    spec = RESOURCE_PRESETS[preset]
    return ResolvedResources(requests=deepcopy(spec["requests"]), limits=deepcopy(spec["limits"]))


def _from_memory_size(memory_limit: str) -> ResolvedResources:
    """历史配额计算方式：内存 request 为 limit 的一半，每 Gi 配 0.25c request / 0.5c limit。"""
    mem_gb = parse_quantity(memory_limit) / (1024**3)
    return ResolvedResources(
        requests={"cpu": f"{mem_gb * 250}m", "memory": f"{mem_gb / 2}Gi"},
        limits={"cpu": f"{mem_gb * 500}m", "memory": memory_limit},
    )
