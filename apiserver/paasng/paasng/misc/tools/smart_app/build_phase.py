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

from django.db import transaction

from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.models import SmartBuildPhase, SmartBuildRecord, SmartBuildStep


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
BUILD_PHASES = [
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
                name="构建 S-Mart 包",
                display_name_en="Build S-Mart package",
                display_name_zh_cn="构建 S-Mart 包",
            ),
        ],
    ),
]


def initialize_build_phases(smart_build: SmartBuildRecord):
    with transaction.atomic():
        for phase_config in BUILD_PHASES:
            phase = SmartBuildPhase.objects.create(
                smart_build=smart_build,
                type=phase_config.type.value,
            )

            SmartBuildStep.objects.bulk_create(
                [
                    SmartBuildStep(
                        phase=phase,
                        name=step.name,
                    )
                    for step in phase_config.steps
                ]
            )


def get_phase(smart_build, phase_type: SmartBuildPhaseType):
    """获取指定类型的阶段"""

    return SmartBuildPhase.objects.get(smart_build=smart_build, type=phase_type.value)
