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
from functools import partial

import pytest
from django_dynamic_fixture import G

from paas_wl.bk_app.cnative.specs.models import create_app_resource, generate_bkapp_name
from paas_wl.bk_app.cnative.specs.procs.replicas import BkAppProcScaler
from paas_wl.bk_app.cnative.specs.resource import deploy
from paas_wl.bk_app.deploy.processes import CNativeProcController, ProcSpecUpdater
from paas_wl.bk_app.processes.constants import DEFAULT_CNATIVE_MAX_REPLICAS, ProcessTargetStatus
from paas_wl.bk_app.processes.models import ProcessSpec, ProcessSpecPlan
from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paasng.platform.bkapp_model.models import ModuleProcessSpec

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def web_proc_factory(bk_module, bk_stag_wl_app):
    G(ModuleProcessSpec, module=bk_module, name="web")
    plan = G(ProcessSpecPlan, max_replicas=DEFAULT_CNATIVE_MAX_REPLICAS)
    return partial(G, ProcessSpec, engine_app=bk_stag_wl_app, name="web", plan=plan)


class TestProcSpecUpdater:
    def test_set_start(self, bk_stag_env, web_proc_factory):
        web_proc_factory(target_replicas=0, target_status=ProcessTargetStatus.STOP.value)

        updater = ProcSpecUpdater(bk_stag_env, "web")
        assert updater.spec_object.target_status == ProcessTargetStatus.STOP.value

        updater.set_start()
        assert updater.spec_object.target_replicas == 1
        assert updater.spec_object.target_status == ProcessTargetStatus.START.value

    def test_set_stop(self, bk_stag_env, web_proc_factory):
        web_proc_factory(target_replicas=2, target_status=ProcessTargetStatus.START.value)

        updater = ProcSpecUpdater(bk_stag_env, "web")
        updater.set_stop()
        assert updater.spec_object.target_replicas == 2
        assert updater.spec_object.target_status == ProcessTargetStatus.STOP.value

    def test_change_replicas_integrated(self, bk_stag_env, web_proc_factory):
        web_proc_factory(target_replicas=0, target_status=ProcessTargetStatus.STOP.value)

        updater = ProcSpecUpdater(bk_stag_env, "web")
        updater.change_replicas(target_replicas=3)
        assert updater.spec_object.target_replicas == 3
        assert updater.spec_object.target_status == ProcessTargetStatus.START.value

        # Set the value to zero should stop the process
        updater.change_replicas(target_replicas=0)
        assert updater.spec_object.target_replicas == 0
        assert updater.spec_object.target_status == ProcessTargetStatus.STOP.value

    def test_set_autoscaling_integrated(self, bk_stag_env, web_proc_factory):
        web_proc_factory(target_replicas=2, target_status=ProcessTargetStatus.START.value)

        # Enable autoscaling
        updater = ProcSpecUpdater(bk_stag_env, "web")
        updater.set_autoscaling(True, AutoscalingConfig(min_replicas=1, max_replicas=3, policy="default"))
        assert updater.spec_object.autoscaling is True
        assert updater.spec_object.scaling_config == AutoscalingConfig(
            min_replicas=1, max_replicas=3, policy="default"
        )

        # Update autoscaling
        updater.set_autoscaling(True, AutoscalingConfig(min_replicas=1, max_replicas=4, policy="default"))
        assert updater.spec_object.autoscaling is True
        assert updater.spec_object.scaling_config == AutoscalingConfig(
            min_replicas=1, max_replicas=4, policy="default"
        )

        # Disable autoscaling
        updater.set_autoscaling(False)
        assert updater.spec_object.autoscaling is False
        assert updater.spec_object.scaling_config == AutoscalingConfig(
            min_replicas=1, max_replicas=4, policy="default"
        ), "The config should remain as it is."


# TODO: Remove duplicated fixture called the same name
@pytest.fixture()
def _deploy_stag_env(bk_stag_env, bk_stag_wl_app, namespace_maker):
    """Deploy a default payload to cluster for stag environment"""
    namespace_maker.make(bk_stag_wl_app.namespace)
    resource = create_app_resource(generate_bkapp_name(bk_stag_env), "nginx:latest")
    deploy(bk_stag_env, resource.to_deployable())


@pytest.mark.skip_when_no_crds()
class TestCNativeProcController:
    @pytest.mark.usefixtures("_deploy_stag_env")
    def test_scale_static_integrated(self, bk_stag_env, web_proc_factory):
        web_proc_factory(target_replicas=1, target_status=ProcessTargetStatus.START.value)

        assert BkAppProcScaler(bk_stag_env).get_replicas("web") == 1
        # Scale the process
        CNativeProcController(bk_stag_env).scale("web", False, 2)
        assert BkAppProcScaler(bk_stag_env).get_replicas("web") == 2

        # Stop the process
        CNativeProcController(bk_stag_env).stop("web")
        assert BkAppProcScaler(bk_stag_env).get_replicas("web") == 0

        # Start the process
        CNativeProcController(bk_stag_env).start("web")
        assert BkAppProcScaler(bk_stag_env).get_replicas("web") == 2

    @pytest.mark.usefixtures("_deploy_stag_env")
    def test_autoscaling_integrated(self, bk_stag_env, bk_stag_wl_app, web_proc_factory):
        web_proc_factory(target_replicas=1, target_status=ProcessTargetStatus.START.value)
        # Turn on the feature flag
        cluster = get_cluster_by_app(bk_stag_wl_app)
        cluster.feature_flags.update({ClusterFeatureFlag.ENABLE_AUTOSCALING: True})
        cluster.save(update_fields=["feature_flags"])

        assert BkAppProcScaler(bk_stag_env).get_autoscaling("web") is None
        CNativeProcController(bk_stag_env).scale(
            "web", True, None, scaling_config=AutoscalingConfig(min_replicas=1, max_replicas=3, policy="default")
        )
        assert BkAppProcScaler(bk_stag_env).get_autoscaling("web") is not None

        # Turn off the autoscaling
        CNativeProcController(bk_stag_env).scale("web", False, None)
        assert BkAppProcScaler(bk_stag_env).get_autoscaling("web") is None

    @pytest.mark.usefixtures("_deploy_stag_env")
    def test_scale_down_to_module_target_replicas(self, bk_stag_env, web_proc_factory):
        """测试 scale down 目标副本数与模块目标副本数( ModuleProcessSpec.target_replicas ) 一致时, 会成功 scale down"""
        web_proc_factory(target_replicas=1, target_status=ProcessTargetStatus.START.value)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_stag_env.module, name="web")
        module_target_replicas = proc_spec.target_replicas
        assert proc_spec.get_target_replicas(bk_stag_env.environment) == module_target_replicas

        # Scale up process
        CNativeProcController(bk_stag_env).scale("web", False, module_target_replicas + 1)
        assert proc_spec.get_target_replicas(bk_stag_env.environment) == module_target_replicas + 1

        # Scale down process
        CNativeProcController(bk_stag_env).scale("web", False, module_target_replicas)
        assert proc_spec.get_target_replicas(bk_stag_env.environment) == module_target_replicas
