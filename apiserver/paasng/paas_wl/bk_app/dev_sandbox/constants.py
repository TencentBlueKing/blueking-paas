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


class SourceCodeFetchMethod(StrStructuredEnum):
    """源码获取方式"""

    HTTP = EnumField("HTTP", label="HTTP File")
    GIT = EnumField("GIT", label="Git Repository")
    BK_REPO = EnumField("BK_REPO", label="BkRepo Tarball")


class DevSandboxStatus(StrStructuredEnum):
    """沙箱状态"""

    READY = EnumField("ready")
    PENDING = EnumField("pending")


class DevSandboxEnvKey(StrStructuredEnum):
    """沙箱环境变量键名称"""

    WORKSPACE = EnumField("WORKSPACE")
    SOURCE_FETCH_METHOD = EnumField("SOURCE_FETCH_METHOD")
    SOURCE_FETCH_URL = EnumField("SOURCE_FETCH_URL")
    TOKEN = EnumField("TOKEN")
    CODE_EDITOR_PASSWORD = EnumField("PASSWORD")
    ENABLE_CODE_EDITOR = EnumField("ENABLE_CODE_EDITOR")


class DevSandboxEnvVarSource(StrStructuredEnum):
    """沙箱环境变量来源"""

    STAG = EnumField("stag", label="预发布环境")
    CUSTOM = EnumField("custom", label="用户自定义")
