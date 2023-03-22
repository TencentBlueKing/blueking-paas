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

from paasng.utils.basic import ChoicesEnum

# 如果日志配置是所有进程通用的, process_type 填充为 "-"
DEFAULT_LOG_CONFIG_PLACEHOLDER = "-"


class LogTimeType(ChoicesEnum):
    """
    日志搜索-日期范围类型
    """

    TYPE_5m = "5m"
    TYPE_1h = "1h"
    TYPE_3h = "3h"
    TYPE_6h = "6h"
    TYPE_12h = "12h"
    TYPE_1d = "1d"
    TYPE_3d = "3d"
    TYPE_7d = "7d"
    TYPE_CUSTOMIZED = "customized"

    _choices_labels = (
        (TYPE_5m, "5分钟"),
        (TYPE_1h, "1小时"),
        (TYPE_3h, "3小时"),
        (TYPE_6h, "6小时"),
        (TYPE_12h, "12小时"),
        (TYPE_1d, "1天"),
        (TYPE_3d, "3天"),
        (TYPE_7d, "7天"),
        (TYPE_CUSTOMIZED, "自定义"),
    )


class LogType(str, StructuredEnum):
    """
    日志类型
    """

    STRUCTURED = EnumField("STRUCTURED", label="结构化日志")
    STANDARD_OUTPUT = EnumField("STANDARD_OUTPUT", label="标准输出日志")
    INGRESS = EnumField("INGRESS", label="接入层日志")


class LogCollectorType(str, StructuredEnum):
    """日志采集器类型"""

    BK_LOG = EnumField("BK_LOG", label="蓝鲸日志平台")
    ELK = EnumField("ELK", label="ELK")
