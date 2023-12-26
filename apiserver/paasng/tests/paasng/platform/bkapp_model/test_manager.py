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
from django_dynamic_fixture import G

from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paasng.platform.bkapp_model.manager import ModuleProcessSpecManager
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.engine.models.deployment import AutoscalingConfig as _AutoscalingConfig

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
