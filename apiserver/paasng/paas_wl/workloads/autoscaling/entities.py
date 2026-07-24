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

from dataclasses import dataclass, field
from typing import List, Optional

import cattr

from paas_wl.bk_app.cnative.specs.constants import ScalingPolicy
from paas_wl.workloads.autoscaling.constants import DEFAULT_METRICS, ScalingMetric, ScalingMetricSourceType


@dataclass
class ScalingObjectRef:
    """自动扩缩容资源引用"""

    api_version: str
    kind: str
    name: str


@dataclass
class MetricSpec:
    """扩缩容指标配置"""

    # 指标来源类型
    type: ScalingMetricSourceType
    # 指标名称
    metric: ScalingMetric
    # 指标值：百分比 / 绝对数值
    value: str
    # 指标来源对象，搭配 Object Type 使用
    described_object: Optional[ScalingObjectRef] = None


@dataclass
class ProcAutoscalingSpec:
    """The specification for ProcAutoscaling kres entity."""

    min_replicas: int
    max_replicas: int
    metrics: List[MetricSpec]


@dataclass
class AutoscalingConfig:
    """自动扩缩容配置"""

    # 最小副本数量
    min_replicas: int
    # 最大副本数量
    max_replicas: int
    # 扩缩容策略
    policy: str
    # 自定义扩缩容指标; 为空时使用 DEFAULT_METRICS
    metrics: List[MetricSpec] = field(default_factory=list)

    def to_autoscaling_spec(self) -> ProcAutoscalingSpec:
        """Transform current config into the autoscaling spec object."""
        # 优先使用用户自定义 metrics
        if self.metrics:
            return ProcAutoscalingSpec(
                min_replicas=self.min_replicas,
                max_replicas=self.max_replicas,
                metrics=self.metrics,
            )
        # 无自定义 metrics 时, 根据 policy 决定默认值
        if self.policy == ScalingPolicy.DEFAULT.value:
            return ProcAutoscalingSpec(
                min_replicas=self.min_replicas,
                max_replicas=self.max_replicas,
                metrics=cattr.structure(DEFAULT_METRICS, List[MetricSpec]),
            )
        raise ValueError("Unable to get metrics, policy: {}".format(self.policy))
