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

import pytest
from django_dynamic_fixture import G

from paas_wl.bk_app.processes.models import PROC_DEFAULT_REPLICAS
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paasng.platform.bkapp_model.entities import AutoscalingConfig as _AutoscalingConfig
from paasng.platform.bkapp_model.manager import ModuleProcessSpecManager
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.engine.models.deployment import ProcessTmpl

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def process_web(bk_module) -> ModuleProcessSpec:
    return G(ModuleProcessSpec, module=bk_module, name="web")


class TestModuleProcessSpecManager:
    def test_set_replicas_integrated(self, bk_module, process_web):
        assert not ProcessSpecEnvOverlay.objects.filter(proc_spec=process_web).exists()

        # Set replicas for both environments
        ModuleProcessSpecManager(bk_module).set_replicas("web", "stag", 2)
        ModuleProcessSpecManager(bk_module).set_replicas("web", "prod", 3)
        assert ProcessSpecEnvOverlay.objects.filter(proc_spec=process_web).count() == 2
        assert ProcessSpecEnvOverlay.objects.get(proc_spec=process_web, environment_name="stag").target_replicas == 2
        assert ProcessSpecEnvOverlay.objects.get(proc_spec=process_web, environment_name="prod").target_replicas == 3

        # Update existent data
        ModuleProcessSpecManager(bk_module).set_replicas("web", "prod", 2)
        assert ProcessSpecEnvOverlay.objects.get(proc_spec=process_web, environment_name="prod").target_replicas == 2

    def test_set_autoscaling_integrated(self, bk_module, process_web):
        assert not ProcessSpecEnvOverlay.objects.filter(proc_spec=process_web).exists()

        # Set replicas for both environments
        ModuleProcessSpecManager(bk_module).set_autoscaling("web", "stag", False)
        ModuleProcessSpecManager(bk_module).set_autoscaling(
            "web", "prod", True, AutoscalingConfig(min_replicas=1, max_replicas=3, policy="default")
        )
        assert ProcessSpecEnvOverlay.objects.filter(proc_spec=process_web).count() == 2
        assert ProcessSpecEnvOverlay.objects.get(proc_spec=process_web, environment_name="stag").autoscaling is False
        assert ProcessSpecEnvOverlay.objects.get(proc_spec=process_web, environment_name="prod").autoscaling is True
        assert ProcessSpecEnvOverlay.objects.get(
            proc_spec=process_web, environment_name="prod"
        ).scaling_config == _AutoscalingConfig(min_replicas=1, max_replicas=3, policy="default")

        # Update existent data
        ModuleProcessSpecManager(bk_module).set_autoscaling("web", "prod", False)
        assert ProcessSpecEnvOverlay.objects.get(proc_spec=process_web, environment_name="prod").autoscaling is False
        assert (
            ProcessSpecEnvOverlay.objects.get(proc_spec=process_web, environment_name="prod").scaling_config
            is not None
        ), "The config should have been preserved as it is"


class TestSyncFromDescMethod:
    """测试 ModuleProcessSpecManager.sync_from_desc 方法"""

    @pytest.fixture()
    def process_with_replicas(self, bk_module) -> ModuleProcessSpec:
        spec = G(ModuleProcessSpec, module=bk_module, name="foo")
        ProcessSpecEnvOverlay.objects.create(proc_spec=spec, environment_name="stag", target_replicas=3)
        ProcessSpecEnvOverlay.objects.create(proc_spec=spec, environment_name="prod", target_replicas=5)
        return spec

    @pytest.mark.parametrize(
        ("proc_name", "replicas", "expected_stag_replicas", "expected_prod_replicas"),
        [
            ("worker", 2, 2, 2),
            ("worker", 1, 1, 1),
            # web 进程具有默认值. stag 环境默认 1, prod 环境默认 2
            ("web", None, 1, 2),
            ("worker", None, 1, 1),
        ],
    )
    def test_sync_replicas_when_create_proc_spec(
        self, proc_name, bk_module, replicas, expected_stag_replicas, expected_prod_replicas
    ):
        ModuleProcessSpecManager(bk_module).sync_from_desc(
            [ProcessTmpl(name=proc_name, command="foo", replicas=replicas)]
        )
        spec = ModuleProcessSpec.objects.get(name=proc_name, module=bk_module)
        assert spec.target_replicas == replicas or PROC_DEFAULT_REPLICAS
        assert spec.get_target_replicas("stag") == expected_stag_replicas
        assert spec.get_target_replicas("prod") == expected_prod_replicas

    @pytest.mark.parametrize(
        ("replicas", "expected_stag_replicas", "expected_prod_replicas"),
        [(2, 2, 2), (1, 1, 1), (None, 3, 5)],
    )
    def test_sync_replicas_when_update_proc_spec(
        self, bk_module, process_with_replicas, replicas, expected_stag_replicas, expected_prod_replicas
    ):
        ModuleProcessSpecManager(bk_module).sync_from_desc(
            [ProcessTmpl(name=process_with_replicas.name, command="bar", replicas=replicas)]
        )
        spec = ModuleProcessSpec.objects.get(name=process_with_replicas.name, module=bk_module)
        assert spec.get_target_replicas("stag") == expected_stag_replicas
        assert spec.get_target_replicas("prod") == expected_prod_replicas
