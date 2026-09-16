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

"""Redis 套餐资源规格。

预设名称与资源数值对齐 Bitnami common resource presets：
https://github.com/bitnami/charts/blob/main/bitnami/common/templates/_resources.tpl
本地静态维护，不在运行时读取模板；生产环境使用前需按集群容量和 Redis 压测结果调整。
"""

from copy import deepcopy
from typing import Dict, NamedTuple

from kubernetes.utils.quantity import parse_quantity

from .entities import RedisPlanConfig, ResourcePresetName

DEFAULT_RESOURCE_PRESET: ResourcePresetName = "micro"

# preset -> {requests, limits}，requests/limits 为任意 K8s 资源字典
RESOURCE_PRESETS: Dict[ResourcePresetName, Dict[str, Dict[str, str]]] = {
    "nano": {
        "requests": {"cpu": "100m", "memory": "128Mi", "ephemeral-storage": "50Mi"},
        "limits": {"cpu": "150m", "memory": "192Mi", "ephemeral-storage": "2Gi"},
    },
    "micro": {
        "requests": {"cpu": "250m", "memory": "256Mi", "ephemeral-storage": "50Mi"},
        "limits": {"cpu": "375m", "memory": "384Mi", "ephemeral-storage": "2Gi"},
    },
    "small": {
        "requests": {"cpu": "500m", "memory": "512Mi", "ephemeral-storage": "50Mi"},
        "limits": {"cpu": "750m", "memory": "768Mi", "ephemeral-storage": "2Gi"},
    },
    "medium": {
        "requests": {"cpu": "500m", "memory": "1024Mi", "ephemeral-storage": "50Mi"},
        "limits": {"cpu": "750m", "memory": "1536Mi", "ephemeral-storage": "2Gi"},
    },
    "large": {
        "requests": {"cpu": "1.0", "memory": "2048Mi", "ephemeral-storage": "50Mi"},
        "limits": {"cpu": "1.5", "memory": "3072Mi", "ephemeral-storage": "2Gi"},
    },
    "xlarge": {
        "requests": {"cpu": "1.0", "memory": "3072Mi", "ephemeral-storage": "50Mi"},
        "limits": {"cpu": "3.0", "memory": "6144Mi", "ephemeral-storage": "2Gi"},
    },
    "2xlarge": {
        "requests": {"cpu": "1.0", "memory": "3072Mi", "ephemeral-storage": "50Mi"},
        "limits": {"cpu": "6.0", "memory": "12288Mi", "ephemeral-storage": "2Gi"},
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
