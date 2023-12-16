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
"""
前置 migrations:
paasng/platform/engine/migrations/0005_auto_20210110_1917.py
paasng/platform/engine/migrations/0010_auto_20211126_1751.py
paasng/platform/engine/migrations/0017_reset_step_meta_set.py
paasng/platform/engine/migrations/0019_auto_20231214_1547.py

最终数据在 step_meta_data.py 维护
"""
from typing import List

from django.core.management.base import BaseCommand

from paasng.platform.engine.constants import DOCKER_BUILD_STEPSET_NAME, IMAGE_RELEASE_STEPSET_NAME
from paasng.platform.engine.management.commands.step_meta_data import (
    ALL_STEP_METAS,
    CNB_SET,
    DEFAULT_SET,
    DOCKER_BUILD_SET,
    IMAGE_RELEASE_SET,
    SLUG_PILOT_SET,
    StepMetaData,
)
from paasng.platform.engine.models.steps import DeployStepMeta, StepMetaSet
from paasng.platform.modules.models.runtime import AppSlugBuilder


class Command(BaseCommand):
    help = "Update StepMetaSet and DeployStepMeta"

    def handle(self, *args, **options):
        # upsert all step metas
        self._upsert_step_metas()
        # upsert step meta set
        self._upsert_default_set()
        self._upsert_cnb_set()
        self._upsert_slug_pilot_set()
        self._upsert_docker_build_set()
        self._upsert_image_release_set()

    def _upsert_step_metas(self):
        """upsert all step metas"""
        for step_name, step in ALL_STEP_METAS.items():
            DeployStepMeta.objects.update_or_create(
                name=step_name,
                phase=step.phase,
                defaults={
                    "display_name_en": step.display_name_en,
                    "display_name_zh_cn": step.display_name_zh_cn,
                    "started_patterns": step.started_patterns or [],
                    "finished_patterns": step.finished_patterns or [],
                },
            )
            self.stdout.write(f"Upserting step {step.name} successfully")

    def _upsert_default_set(self):
        step_meta_set_obj, _ = StepMetaSet.objects.update_or_create(
            name="default",
            is_default=True,
        )
        self._readd_metas(step_meta_set_obj, DEFAULT_SET)

    def _upsert_cnb_set(self):
        step_meta_set_obj, _ = StepMetaSet.objects.update_or_create(name="cnb", is_default=True)
        self._readd_metas(step_meta_set_obj, CNB_SET)

    def _upsert_slug_pilot_set(self):
        # slug-pilot 对应 tencent 版本的 builder_provider, slug-pilot-ieod 对应上云版本的 builder_provider
        for set_name in ["slug-pilot", "slug-pilot-ieod"]:
            # 可单独更新 builder_provider
            step_meta_set_obj, _ = StepMetaSet.objects.update_or_create(name=set_name, is_default=False)
            self._readd_metas(step_meta_set_obj, SLUG_PILOT_SET)

        # 私有化版本只有一个 slug-pilot, 并且绑定名字是 blueking 的 builder_provider
        if slug_builder := AppSlugBuilder.objects.filter(name="blueking").last():
            StepMetaSet.objects.filter(name="slug-pilot").update(builder_provider=slug_builder)

    def _upsert_docker_build_set(self):
        step_meta_set_obj, _ = StepMetaSet.objects.update_or_create(name=DOCKER_BUILD_STEPSET_NAME, is_default=False)
        self._readd_metas(step_meta_set_obj, DOCKER_BUILD_SET)

    def _upsert_image_release_set(self):
        step_meta_set_obj, _ = StepMetaSet.objects.update_or_create(name=IMAGE_RELEASE_STEPSET_NAME, is_default=False)
        self._readd_metas(step_meta_set_obj, IMAGE_RELEASE_SET)

    def _readd_metas(self, step_meta_set_obj: StepMetaSet, expected_step_set: List[StepMetaData]):
        """重新添加 metas. 如果 metas 已经和目标步骤集一致, 则直接返回

        :param step_meta_set_obj: StepMetaSet 实例
        :param expected_step_set: 期望的步骤集
        """
        current_step_names = list(
            step_meta_set_obj.metas.through.objects.filter(stepmetaset_id=step_meta_set_obj.pk)
            .order_by("id")
            .values_list("deploystepmeta__name", flat=True)
        )
        expected_step_names = [step.name for step in expected_step_set]

        # 步骤正确直接返回
        if current_step_names == expected_step_names:
            return

        step_meta_set_obj.metas.clear()
        for step_meta in expected_step_set:
            step_meta_set_obj.metas.add(DeployStepMeta.objects.filter(name=step_meta.name).last())

        self.stdout.write(f"Recreate metas for {step_meta_set_obj.name} set successfully")
