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

from paas_wl.bk_app.cnative.specs.models import create_app_resource
from paas_wl.bk_app.cnative.specs.procs.exceptions import ProcNotDeployed, ProcNotFoundInRes
from paas_wl.bk_app.cnative.specs.procs.replicas import BkAppProcScaler
from paas_wl.bk_app.cnative.specs.resource import deploy
from paas_wl.core.resource import generate_bkapp_name
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def _deploy_stag_env(bk_stag_env, bk_stag_wl_app, _with_stag_ns):
    """Deploy a default payload to cluster for stag environment"""
    resource = create_app_resource(generate_bkapp_name(bk_stag_env), "nginx:latest")
    deploy(bk_stag_env, resource.to_deployable())


@pytest.mark.skip_when_no_crds()
class TestBkAppProcScaler:
    def test_scale_not_deployed(self, bk_stag_env, bk_stag_wl_app):
        with pytest.raises(ProcNotDeployed):
            BkAppProcScaler(bk_stag_env).set_replicas("web", 1)

    @pytest.mark.usefixtures("_deploy_stag_env")
    def test_scale_proc_not_found(self, bk_stag_env):
        with pytest.raises(ProcNotFoundInRes):
            BkAppProcScaler(bk_stag_env).set_replicas("invalid-name", 1)

    @pytest.mark.usefixtures("_deploy_stag_env")
    def test_scale_integrated(self, bk_stag_env):
        assert BkAppProcScaler(bk_stag_env).get_replicas("web") == 1
        BkAppProcScaler(bk_stag_env).set_replicas("web", 2)
        assert BkAppProcScaler(bk_stag_env).get_replicas("web") == 2

    def test_set_autoscaling_not_deployed(self, bk_stag_env, bk_stag_wl_app):
        with pytest.raises(ProcNotDeployed):
            BkAppProcScaler(bk_stag_env).set_autoscaling(
                "invalid-name", True, AutoscalingConfig(min_replicas=1, max_replicas=1, policy="default")
            )

    @pytest.mark.usefixtures("_deploy_stag_env")
    def test_set_autoscaling_integrated(self, bk_stag_env, bk_stag_wl_app):
        assert BkAppProcScaler(bk_stag_env).get_autoscaling("web") is None

        # Enable the autoscaling
        BkAppProcScaler(bk_stag_env).set_autoscaling(
            "web", True, AutoscalingConfig(min_replicas=1, max_replicas=1, policy="default")
        )
        assert BkAppProcScaler(bk_stag_env).get_autoscaling("web") == {
            "min_replicas": 1,
            "max_replicas": 1,
            "policy": "default",
        }

        # Update the autoscaling config
        BkAppProcScaler(bk_stag_env).set_autoscaling(
            "web", True, AutoscalingConfig(min_replicas=2, max_replicas=2, policy="default")
        )
        assert BkAppProcScaler(bk_stag_env).get_autoscaling("web") == {
            "min_replicas": 2,
            "max_replicas": 2,
            "policy": "default",
        }

        # Disable the autoscaling
        BkAppProcScaler(bk_stag_env).set_autoscaling("web", False, None)
        assert BkAppProcScaler(bk_stag_env).get_autoscaling("web") is None
