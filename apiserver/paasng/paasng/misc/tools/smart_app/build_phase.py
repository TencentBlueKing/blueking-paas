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

from dataclasses import dataclass
from typing import List

from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType


@dataclass
class StepConfig:
    """构建步骤配置"""

    name: str
    display_name_en: str
    display_name_zh_cn: str


@dataclass
class PhaseConfig:
    """构建阶段配置"""

    type: SmartBuildPhaseType
    display_name_en: str
    display_name_zh_cn: str
    steps: List[StepConfig]


# 定义所有阶段和步骤
ALL_SMART_BUILD_PHASES = [
    PhaseConfig(
        type=SmartBuildPhaseType.PREPARATION,
        display_name_en="Preparation",
        display_name_zh_cn="准备阶段",
        steps=[
            StepConfig(
                name="校验应用描述文件",
                display_name_en="Verify application description file",
                display_name_zh_cn="校验应用描述文件",
            ),
        ],
    ),
    PhaseConfig(
        type=SmartBuildPhaseType.BUILD,
        display_name_en="Build",
        display_name_zh_cn="构建阶段",
        steps=[
            StepConfig(
                name="准备构建环境",
                display_name_en="Prepare build environment",
                display_name_zh_cn="准备构建环境",
            ),
            StepConfig(
                name="构建 S-Mart 包",
                display_name_en="Build S-Mart package",
                display_name_zh_cn="构建 S-Mart 包",
            ),
        ],
    ),
]
