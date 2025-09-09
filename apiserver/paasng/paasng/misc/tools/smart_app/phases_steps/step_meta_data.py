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

from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType


@define
class StepMetaData:
    name: str
    display_name_en: str
    display_name_zh_cn: str
    phase: str

    def __attrs_post_init__(self):
        if self.name in ALL_STEP_METAS:
            raise ValueError(f"Duplicated step name: {self.name}")
        # Register this step metadata to the global dictionary
        ALL_STEP_METAS[self.name] = self


ALL_STEP_METAS: Dict[str, StepMetaData] = {}

###### Phase: PREPARATION ######
VALIDATE_APP_DESC_FILE = StepMetaData(
    name="校验应用描述文件",
    display_name_en="Verify application description file",
    display_name_zh_cn="校验应用描述文件",
    phase=SmartBuildPhaseType.PREPARATION.value,
)


##### Phase: BUILDING ######
INITIALIZE_BUILD_ENV = StepMetaData(
    name="初始化构建环境",
    display_name_en="Initialize build environment",
    display_name_zh_cn="初始化构建环境",
    phase=SmartBuildPhaseType.BUILD.value,
)

BUILD_SMART_PACKAGE = StepMetaData(
    name="构建 S-Mart 包",
    display_name_en="Build S-Mart package",
    display_name_zh_cn="构建 S-Mart 包",
    phase=SmartBuildPhaseType.BUILD.value,
)
