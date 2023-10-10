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


class ETLType(str, StructuredEnum):
    DELIMITER = EnumField("bk_log_delimiter")
    REGEXP = EnumField("bk_log_regexp")
    JSON = EnumField("bk_log_json")
    TEXT = EnumField("bk_log_text")


class FieldType(str, StructuredEnum):
    INT = EnumField("int")
    LONG = EnumField("long")
    DOUBLE = EnumField("double")
    STRING = EnumField("string")
    OBJECT = EnumField("object")
    NESTED = EnumField("nested")


class BkLogType(str, StructuredEnum):
    JSON = EnumField("json")
    STDOUT = EnumField("stdout")
