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

from paasng.platform.engine.constants import DOCKER_BUILD_STEPSET_NAME, IMAGE_RELEASE_STEPSET_NAME, RuntimeType
from paasng.platform.engine.exceptions import DuplicateNameInSamePhaseError, StepNotInPresetListError
from paasng.platform.engine.models.phases import DeployPhaseTypes
from paasng.platform.engine.models.steps import DeployStepMeta, StepMetaSet
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


def setup_dockerbuild_stepmeta():
    """初始化 dockerbuild 的「构建阶段」的构建步骤"""
    DeployStepMeta.objects.update_or_create(
        phase=DeployPhaseTypes.BUILD,
        name="下载构建上下文",
        defaults={
            "display_name_zh_cn": "下载构建上下文",
            "display_name_en": "Download docker build context",
            "started_patterns": [r"Downloading docker build context\.\.\."],
            "finished_patterns": [r"\* Docker build context is ready"],
        },
    )

    DeployStepMeta.objects.update_or_create(
        phase=DeployPhaseTypes.BUILD,
        name="构建镜像",
        defaults={
            "display_name_zh_cn": "构建镜像",
            "display_name_en": "Building image",
            "started_patterns": [r"Start building\.\.\."],
            "finished_patterns": [r"\* Build success"],
        },
    )


def bind_step_to_metaset(metaset: StepMetaSet, phase: DeployPhaseTypes, step_name: str):
    try:
        metaset.metas.get(phase=phase, name=step_name)
    except DeployStepMeta.DoesNotExist:
        try:
            step_meta = DeployStepMeta.objects.get(phase=phase, name=step_name)
        except DeployStepMeta.DoesNotExist:
            return
        except DeployStepMeta.MultipleObjectsReturned:
            step_meta = DeployStepMeta.objects.filter(phase=phase, name=step_name)[0]
        metaset.metas.add(step_meta)


def setup_dockerbuild_metaset() -> StepMetaSet:
    """初始化 dockerbuild 的构建步骤"""
    setup_dockerbuild_stepmeta()
    metaset, created = StepMetaSet.objects.update_or_create(
        defaults={
            "is_default": False,
        },
        name=DOCKER_BUILD_STEPSET_NAME,
    )
    if not created:
        return metaset

    steps = [
        (DeployPhaseTypes.PREPARATION, "解析应用进程信息"),
        (DeployPhaseTypes.PREPARATION, "上传仓库代码"),
        (DeployPhaseTypes.PREPARATION, "配置资源实例"),
        (DeployPhaseTypes.BUILD, "下载构建上下文"),
        (DeployPhaseTypes.BUILD, "构建镜像"),
        (DeployPhaseTypes.RELEASE, "部署应用"),
        (DeployPhaseTypes.RELEASE, "检测部署结果"),
    ]
    for phase, step_name in steps:
        bind_step_to_metaset(metaset, phase, step_name)
    return metaset


def setup_image_release_metaset() -> StepMetaSet:
    """初始化 image release 的构建步骤"""
    metaset, created = StepMetaSet.objects.update_or_create(
        defaults={
            "is_default": False,
        },
        name=IMAGE_RELEASE_STEPSET_NAME,
    )
    if not created:
        return metaset

    steps = [
        (DeployPhaseTypes.PREPARATION, "解析应用进程信息"),
        (DeployPhaseTypes.PREPARATION, "配置资源实例"),
        (DeployPhaseTypes.RELEASE, "部署应用"),
        (DeployPhaseTypes.RELEASE, "检测部署结果"),
    ]
    for phase, step_name in steps:
        bind_step_to_metaset(metaset, phase, step_name)
    return metaset


class DeployStepPicker:
    """部署步骤选择器"""

    @classmethod
    def pick(cls, engine_app: "EngineApp") -> StepMetaSet:  # noqa: PLR0911
        """通过 engine_app 选择部署阶段应该绑定的步骤"""
        m = ModuleRuntimeManager(engine_app.env.module)
        if m.build_config.build_method == RuntimeType.DOCKERFILE:
            try:
                return StepMetaSet.objects.get(name=DOCKER_BUILD_STEPSET_NAME)
            except StepMetaSet.DoesNotExist:
                return setup_dockerbuild_metaset()
        elif m.build_config.build_method == RuntimeType.CUSTOM_IMAGE:
            try:
                return StepMetaSet.objects.get(name=IMAGE_RELEASE_STEPSET_NAME)
            except StepMetaSet.DoesNotExist:
                return setup_image_release_metaset()

        # 以 SlugBuilder 匹配为主, 不存在绑定直接走缺省步骤集
        builder = m.get_slug_builder(raise_exception=False)
        if builder is None:
            return cls._get_default_meta_set()

        # TODO 简化模型关系: StepMetaSet 增加 builder_provider 字段, 替代 DeployStepMeta.builder_provider
        meta_sets = StepMetaSet.objects.filter(metas__builder_provider=builder).order_by("-created").distinct()
        if not meta_sets:
            return cls._get_default_meta_set()

        # NOTE: 目前一个 builder 只会关联一个 StepMetaSet
        return meta_sets[0]

    @classmethod
    def _get_default_meta_set(cls):
        """防止由于后台配置缺失而影响部署流程, 绑定默认的 StepMetaSet"""
        try:
            best_matched_set = StepMetaSet.objects.get(is_default=True)
        except StepMetaSet.DoesNotExist:
            best_matched_set = StepMetaSet.objects.all().latest("-created")
        except StepMetaSet.MultipleObjectsReturned:
            best_matched_set = StepMetaSet.objects.filter(is_default=True).order_by("-created")[0]
        return best_matched_set


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
