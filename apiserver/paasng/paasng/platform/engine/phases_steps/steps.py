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
import logging
import re
from contextlib import suppress
from typing import TYPE_CHECKING, Dict, List

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.engine.constants import DOCKER_BUILD_STEPSET_NAME, IMAGE_RELEASE_STEPSET_NAME, RuntimeType
from paasng.platform.engine.exceptions import DuplicateNameInSamePhaseError, StepNotInPresetListError
from paasng.platform.engine.models.phases import DeployPhaseTypes
from paasng.platform.engine.models.steps import StepMetaSet
from paasng.platform.engine.utils.output import RedisChannelStream
from paasng.platform.modules.helpers import ModuleRuntimeManager

if TYPE_CHECKING:
    from paasng.platform.engine.models import EngineApp
    from paasng.platform.engine.models.phases import DeployPhase
    from paasng.platform.engine.models.steps import DeployStep


logger = logging.getLogger()


def get_sorted_steps(phase: "DeployPhase") -> List["DeployStep"]:
    """获取有序的 Steps 列表"""
    names = list(
        DeployStepPicker.pick(engine_app=phase.engine_app).list_sorted_step_names(DeployPhaseTypes(phase.type))
    )
    steps = list(phase.steps.all())

    # 如果出现异常, 就直接返回未排序的步骤.
    # 导致异常的可能情况: 未在 DeployStepMeta 定义的步骤无法排序
    with suppress(IndexError, ValueError):
        steps.sort(key=lambda x: names.index(x.name))
    return steps


class DeployStepPicker:
    """部署步骤选择器"""

    @classmethod
    def pick(cls, engine_app: "EngineApp") -> StepMetaSet:  # noqa: PLR0911
        """通过 engine_app 选择部署阶段应该绑定的步骤

        note: 通过 python manage.py upsert_step_meta_set 来更新步骤集
        """
        m = ModuleRuntimeManager(engine_app.env.module)

        if m.build_config.build_method == RuntimeType.DOCKERFILE:
            return StepMetaSet.objects.get(name=DOCKER_BUILD_STEPSET_NAME)
        elif m.build_config.build_method == RuntimeType.CUSTOM_IMAGE:
            return StepMetaSet.objects.get(name=IMAGE_RELEASE_STEPSET_NAME)

        return cls._pick_default_meta_set(m)

    @classmethod
    def _pick_default_meta_set(cls, m: ModuleRuntimeManager):
        """以 SlugBuilder 匹配为主, 不存在绑定直接走缺省步骤集"""
        if builder := m.get_slug_builder(raise_exception=False):  # noqa: SIM102
            # NOTE: 一个 builder 只会关联一个 StepMetaSet
            if builder.step_meta_set:
                return builder.step_meta_set

        if m.module.application.type == ApplicationType.CLOUD_NATIVE.value:
            return StepMetaSet.objects.filter(is_default=True, name="cnb").order_by("-created").first()
        else:
            return StepMetaSet.objects.filter(is_default=True, name="default").order_by("-created").first()


def update_step_by_line(line: str, pattern_maps: Dict, phase: "DeployPhase"):
    """Try to find a match for the given log line in the given pattern maps. If a
    match is found, update the step status and write to stream.

    :param line: The log line to match.
    :param patterns_maps: The pattern maps to match against.
    :param phase: The deployment phase.
    """
    for job_status, pattern_map in pattern_maps.items():
        for pattern, step_name in pattern_map.items():
            match = re.compile(pattern).findall(line)
            # 未能匹配上任何预设匹配集
            if not match:
                continue

            try:
                step_obj = phase.get_step_by_name(step_name)
            except (StepNotInPresetListError, DuplicateNameInSamePhaseError):
                logger.debug("Step not found or duplicated, name: %s", step_name)
                continue

            # 由于日志会被重复处理，所以肯定会重复判断，当状态一致或处于已结束状态时，跳过
            if step_obj.status == job_status.value or step_obj.is_completed:
                continue

            logger.info("[%s] going to mark & write to stream", phase.deployment.id)
            # 更新 step 状态，并写到输出流
            step_obj.mark_and_write_to_stream(RedisChannelStream.from_deployment_id(phase.deployment.id), job_status)
