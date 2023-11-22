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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext as _

# 添加注解 compute-by-limits=true 后，CPU 计算 Utilization 时
# 将根据当前使用量 & limits 来计算目标副本数，否则默认使用 requests 来计算
GPA_COMPUTE_BY_LIMITS_ANNO_KEY = "compute-by-limits"


class ScalingMetricName(str, StructuredEnum):
    """扩缩容指标名称（用于组装 CPA 的指标）"""

    CPU = EnumField('cpu')
    MEMORY = EnumField('memory')


class ScalingMetricSourceType(str, StructuredEnum):
    """扩缩容指标类型"""

    RESOURCE = EnumField('Resource')
    PODS = EnumField('Pods')
    OBJECT = EnumField('Object')


class ScalingMetricTargetType(str, StructuredEnum):
    """扩缩容指标计量类型（用于组装 CPA 的指标类型）"""

    UTILIZATION = EnumField('Utilization')
    AVERAGE_VALUE = EnumField('AverageValue')


class ScalingEnvName(str, StructuredEnum):
    """扩缩容生效环境"""

    STAG = EnumField('stag', label='仅测试环境')
    PROD = EnumField('prod', label='仅生产环境')
    GLOBAL = EnumField('_global_', label='所有环境')


class ScalingMetric(str, StructuredEnum):
    """扩缩容指标（用户可选指标）"""

    CPU_UTILIZATION = EnumField('cpuUtilization', label=_('CPU 使用率'))
    MEMORY_UTILIZATION = EnumField('memoryUtilization', label=_('内存使用率'))
    CPU_AVERAGE_VALUE = EnumField('cpuAverageValue', label=_('CPU 使用量'))
    MEMORY_AVERAGE_VALUE = EnumField('memoryAverageValue', label=_('内存使用量'))


# The default metrics for autoscaling, do not support customize at this time
DEFAULT_METRICS = [
    {
        "type": 'Resource',
        "metric": 'cpuUtilization',
        "value": '85',
    },
]
