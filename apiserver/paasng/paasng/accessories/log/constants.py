# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

from blue_krill.data_types.enum import EnumField, StructuredEnum

# 如果日志配置是所有进程通用的, process_type 填充为 "-"
DEFAULT_LOG_CONFIG_PLACEHOLDER = "-"
# 默认查询日志的分片大小
DEFAULT_LOG_BATCH_SIZE = 200


class LogTimeChoices(str, StructuredEnum):
    """日志搜索-日期范围可选值"""

    FIVE_MINUTES = EnumField("5m", label="5分钟")
    ONE_HOUR = EnumField("1h", label="1小时")
    THREE_HOURS = EnumField("3h", label="3小时")
    SIX_HOURS = EnumField("6h", label="6小时")
    TWELVE_HOURS = EnumField("12h", label="12小时")
    ONE_DAY = EnumField("1d", label="1天")
    THREE_DAYS = EnumField("3d", label="3天")
    SEVEN_DAYS = EnumField("7d", label="7天")
    CUSTOMIZED = EnumField("customized", label="自定义")


class LogType(str, StructuredEnum):
    """
    日志类型
    """

    STRUCTURED = EnumField("STRUCTURED", label="结构化日志")
    STANDARD_OUTPUT = EnumField("STANDARD_OUTPUT", label="标准输出日志")
    INGRESS = EnumField("INGRESS", label="接入层日志")


class LogCollectorType(str, StructuredEnum):
    """日志采集器类型"""

    BK_LOG = EnumField("BK_LOG", label="蓝鲸日志平台采集器")
    ELK = EnumField("ELK", label="平台内置的 ELK 采集器")
