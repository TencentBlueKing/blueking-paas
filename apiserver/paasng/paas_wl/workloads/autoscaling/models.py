# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from dataclasses import dataclass
from typing import List

from paas_wl.workloads.autoscaling.constants import ScalingMetricName, ScalingMetricType


@dataclass
class ScalingMetric:
    """扩缩容指标配置"""

    # 指标名称：cpu / memory
    name: ScalingMetricName
    # 指标类型：AverageValue / Utilization
    type: ScalingMetricType
    # 指标值：当类型为 Utilization 时，单位为 %
    # 当类型为 AverageValue 时，单位为 m(cpu)/Mi(memory)
    value: int


@dataclass
class AutoscalingConfig:
    """自动扩缩容配置"""

    # 最小副本数量
    min_replicas: int
    # 最大副本数量
    max_replicas: int
    # 扩缩容指标（资源 cpu/memory 等）
    metrics: List[ScalingMetric]
