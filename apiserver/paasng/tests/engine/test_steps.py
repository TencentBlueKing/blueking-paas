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
import pytest

from paasng.engine.models import Deployment, DeployPhaseTypes
from paasng.engine.models.steps import DeployStepMeta, DeployStepPicker, StepMetaSet
from paasng.platform.modules.helpers import ModuleRuntimeBinder
from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner

pytestmark = pytest.mark.django_db


class TestDeployStepPicker:
    """测试 DeployStep"""

    @pytest.fixture(autouse=True)
    def setup_slugbuilder(self, bk_deployment):
        """测试 slug 池"""
        builders = []
        runners = []
        for i in range(5):
            params = dict(
                image="dummy-image",
                tag="latest",
                name=f"dummy+image+{i}",
                region=bk_deployment.app_environment.module.region,
            )
            builders.append(AppSlugBuilder.objects.create(**params))
            runners.append(AppSlugRunner.objects.create(**params))

    @pytest.fixture
    def runtime_binder(self, bk_deployment):
        return ModuleRuntimeBinder(bk_deployment.app_environment.module)

    @pytest.fixture
    def make_step_meta_set(self):
        """动态创建测试步骤集"""

        def _make_step_meta_set(step_set_name: str, slug_provider_name: str):
            meta_set = StepMetaSet.objects.create(name=step_set_name)
            meta_set.metas.add(
                DeployStepMeta.objects.create(
                    phase=DeployPhaseTypes.BUILD.value,
                    name="BUILDER-PROVIDER-STEP",
                    builder_provider=AppSlugBuilder.objects.get(name=slug_provider_name),
                )
            )
            return meta_set

        return _make_step_meta_set

    @pytest.mark.parametrize(
        "preset_step_meta_sets, bind_slug_name, expected",
        [
            # 正常的步骤集匹配
            (
                # 预设的步骤集
                [
                    # step_set_name, builder_name
                    ("dummy+step+set+1", "dummy+image+1"),
                    ("dummy+step+set+2", "dummy+image+2"),
                ],
                # engine_app 绑定的 builder_name
                "dummy+image+1",
                # 预期获取到的步骤集 name
                "dummy+step+set+1",
            ),
            # 绑定的镜像没有创建对应的步骤集，直接使用 default 步骤集
            (
                [
                    ("dummy+step+set+1", "dummy+image+1"),
                    ("dummy+step+set+2", "dummy+image+1"),
                ],
                "dummy+image+3",
                "default",
            ),
            # 匹配到多个步骤集, 使用最新创建的
            (
                [
                    ("dummy+step+set+2", "dummy+image+1"),
                    ("dummy+step+set+1", "dummy+image+1"),
                ],
                "dummy+image+1",
                "dummy+step+set+1",
            ),
        ],
    )
    def test_pick(
        self,
        preset_step_meta_sets,
        bind_slug_name,
        expected,
        runtime_binder,
        make_step_meta_set,
        bk_deployment: Deployment,
    ):
        """测试选择步骤集"""
        slugrunner = AppSlugRunner.objects.get(name=bind_slug_name)
        slugbuilder = AppSlugBuilder.objects.get(name=bind_slug_name)
        runtime_binder.bind_image(
            slugrunner=slugrunner,
            slugbuilder=slugbuilder,
        )
        for preset in preset_step_meta_sets:
            make_step_meta_set(*preset)

        meta_set = DeployStepPicker.pick(bk_deployment.get_engine_app())
        assert meta_set.name == expected

    def test_pick_no_runtime(self, bk_deployment):
        meta_set = DeployStepPicker.pick(bk_deployment.get_engine_app())
        assert meta_set.name == "default"
        assert meta_set.is_default
