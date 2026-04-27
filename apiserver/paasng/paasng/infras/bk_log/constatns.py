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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class ETLType(StrStructuredEnum):
    DELIMITER = EnumField("bk_log_delimiter")
    REGEXP = EnumField("bk_log_regexp")
    JSON = EnumField("bk_log_json")
    TEXT = EnumField("bk_log_text")


class FieldType(StrStructuredEnum):
    INT = EnumField("int")
    LONG = EnumField("long")
    DOUBLE = EnumField("double")
    STRING = EnumField("string")
    OBJECT = EnumField("object")
    NESTED = EnumField("nested")


class BkLogType(StrStructuredEnum):
    JSON = EnumField("json")
    STDOUT = EnumField("stdout")


# 平台级共享采集项的 name_en 模板（JSON 日志 / 标准输出日志）
#
# 启用 ENABLE_SHARED_BK_LOG_INDEX 后, 同一租户下的所有 SaaS 应用共用这两个
# 采集项, 共用同一份 ES 索引; 不同租户通过后缀 {tenant_id} 区分, 落到不同的 ES 索引。
# 应用级隔离靠查询侧按 __ext.labels.bkapp_paas_bk_tencent_com_code 过滤实现。
PLATFORM_INDEX_NAME_JSON_TEMPLATE = "bkpaas_platform_log_json_{tenant_id}"
PLATFORM_INDEX_NAME_STDOUT_TEMPLATE = "bkpaas_platform_log_stdout_{tenant_id}"
