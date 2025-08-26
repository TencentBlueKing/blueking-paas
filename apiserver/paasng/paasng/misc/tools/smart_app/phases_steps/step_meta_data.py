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

from typing import Dict

from attrs import define

from paasng.misc.tools.smart_app.models import SmartBuildPhaseType

@define
class StepMetaData:
    name: str
    display_name_en: str
    display_name_zh_cn: str
    phase: str

    def __attrs_post_init__(self):
        if self.name in ALL_STEP_METAS:
            raise ValueError(f"Duplicated step name: {self.name}")

ALL_STEP_METAS: Dict[str, StepMetaData] = {}

###### Phase: PREPARATION ######
VALIDATE_APP_DESC_FILE = StepMetaData(
    name="校验应用描述文件",
    display_name_en="Verify application description file",
    display_name_zh_cn="校验应用描述文件",
    phase=SmartBuildPhaseType.PREPARATION.value,
)

VALIDATE_FILE_DIRECTORY = StepMetaData(
    name="校验文件目录",
    display_name_en="Verify file directory",
    display_name_zh_cn="校验文件目录",
    phase=SmartBuildPhaseType.PREPARATION.value,
)

SCAN_SENSITIVE_INFO = StepMetaData(
    name="敏感信息扫描",
    display_name_en="Scan sensitive information",
    display_name_zh_cn="敏感信息扫描",
    phase=SmartBuildPhaseType.PREPARATION.value,
)

##### Phase: BUILDING ######
INITIALIZE_BUILD_ENV = StepMetaData(
    name="初始化构建环境",
    display_name_en="Initialize build environment",
    display_name_zh_cn="初始化构建环境",
    phase=SmartBuildPhaseType.BUILD.value,
)

ANALYZE_BUILD_PLAN = StepMetaData(
    name="分析构建方案",
    display_name_en="Analysis the construction plan",
    display_name_zh_cn="分析构建方案",
    phase=SmartBuildPhaseType.BUILD.value,
)

CHECK_BUILD_TOOLS = StepMetaData(
    name="检查构建工具",
    display_name_en="Check build tools",
    display_name_zh_cn="检查构建工具",
    phase=SmartBuildPhaseType.BUILD.value,
)

BUILD_SMART_PACKAGE = StepMetaData(
    name="构建 S-Mart 包",
    display_name_en="Build S-Mart package",
    display_name_zh_cn="构建 S-Mart 包",
    phase=SmartBuildPhaseType.BUILD.value,
)
