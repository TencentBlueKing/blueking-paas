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


class ScalingMetricSourceType(str, StructuredEnum):
    """扩缩容指标来源类型"""

    RESOURCE = EnumField('Resource')


class ScalingMetricName(str, StructuredEnum):
    """扩缩容指标名称"""

    CPU = EnumField('cpu')
    MEMORY = EnumField('memory')


class ScalingMetricType(str, StructuredEnum):
    """扩缩容指标类型"""

    UTILIZATION = EnumField('Utilization')
    AVERAGE_VALUE = EnumField('AverageValue')


class ScalingEnvName(str, StructuredEnum):
    """扩缩容生效环境"""

    # TODO 普通应用暂时使用不上，云原生应用会用到
    STAG = EnumField('stag', label='仅测试环境')
    PROD = EnumField('prod', label='仅生产环境')
    GLOBAL = EnumField('_global_', label='所有环境')
