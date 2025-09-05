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

import logging
from contextlib import suppress
from typing import List

from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.models import SmartBuildPhase, SmartBuildStep

from .step_meta_data import ALL_STEP_METAS

logger = logging.getLogger()


def get_sorted_steps(phase: "SmartBuildPhase") -> List["SmartBuildStep"]:
    """获取所有的 Steps 列表, 排序情况按照在 StepMetaData 中定义的顺序"""

    step_names = [s.name for s in ALL_STEP_METAS.values() if s.phase == phase.type.value]
    steps = list(phase.steps.all())

    # 如果出现异常, 就直接返回未排序的步骤.
    # 导致异常的可能情况: 未在 DeployStepMeta 定义的步骤无法排序
    with suppress(IndexError, ValueError):
        steps.sort(key=lambda x: step_names.index(x.name))
    return steps


class SmartBuildStepManager:
    """s-mart build 步骤管理器"""

    @staticmethod
    def create_step_instances(smart_build_phase: SmartBuildPhase, phase_type: SmartBuildPhaseType):
        """创建当前阶段的所有步骤实例"""
        # 获取指定阶段的所有步骤元数据
        step_metas = [meta for meta in ALL_STEP_METAS.values() if meta.phase == phase_type.value]

        for step_meta in step_metas:
            SmartBuildStep.objects.create(name=step_meta.name, phase=smart_build_phase)
