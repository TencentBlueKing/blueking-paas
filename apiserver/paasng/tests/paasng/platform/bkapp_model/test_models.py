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

from paasng.platform.bkapp_model.constants import ResQuotaPlan
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay

pytestmark = pytest.mark.django_db


@pytest.fixture()
def proc_web(bk_module) -> ModuleProcessSpec:
    return G(ModuleProcessSpec, module=bk_module, name="web", command=["python"], args=["-m", "http.server"])


class TestProcessSpecEnvOverlayManager:
    def test_create(self, bk_module, proc_web):
        ProcessSpecEnvOverlay.objects.save_by_module(
            bk_module,
            proc_web.name,
            "prod",
            target_replicas=2,
            autoscaling=True,
            scaling_config={"min_replicas": 1, "max_replicas": 10, "policy": "default"},
        )

        spec_overlay = ProcessSpecEnvOverlay.objects.get(proc_spec=proc_web, environment_name="prod")
        assert spec_overlay.target_replicas == 2
        assert spec_overlay.autoscaling is True
        assert spec_overlay.scaling_config.max_replicas == 10

    def test_update(self, bk_module, proc_web):
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_web,
            environment_name="stag",
            target_replicas=2,
            plan_name=ResQuotaPlan.P_DEFAULT,
            autoscaling=True,
            scaling_config={"min_replicas": 1, "max_replicas": 1, "policy": "default"},
        )

        ProcessSpecEnvOverlay.objects.save_by_module(
            bk_module,
            proc_web.name,
            "stag",
            target_replicas=2,
            autoscaling=False,
        )

        spec_overlay = ProcessSpecEnvOverlay.objects.get(proc_spec=proc_web, environment_name="stag")
        assert spec_overlay.autoscaling is False
        assert spec_overlay.scaling_config is None
