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

from paasng.platform.bkapp_model.constants import ResQuotaPlan
from paasng.platform.bkapp_model.entities import (
    AutoscalingConfig,
    AutoscalingOverlay,
    ReplicasOverlay,
    ResQuotaOverlay,
)
from paasng.platform.bkapp_model.entities_syncer import sync_proc_env_overlays
from paasng.platform.bkapp_model.models import ProcessSpecEnvOverlay

pytestmark = pytest.mark.django_db


class Test__sync_proc_env_overlays:
    @pytest.fixture(autouse=True)
    def _setup(self, bk_module, proc_web, proc_celery):
        G(
            ProcessSpecEnvOverlay,
            proc_spec=proc_web,
            environment_name="stag",
            target_replicas=2,
            plan_name=ResQuotaPlan.P_DEFAULT,
            autoscaling=True,
            scaling_config={"min_replicas": 1, "max_replicas": 1, "policy": "default"},
        )
        G(
            ProcessSpecEnvOverlay,
            proc_spec=proc_celery,
            environment_name="prod",
            target_replicas=1,
            plan_name=ResQuotaPlan.P_4C2G,
            autoscaling=False,
        )

    def test_only_replicas(self, bk_module, proc_web, proc_celery):
        assert ProcessSpecEnvOverlay.objects.count() == 2

        ret = sync_proc_env_overlays(
            bk_module,
            [
                ReplicasOverlay(env_name="prod", process="web", count="2"),
                ReplicasOverlay(env_name="prod", process="worker", count="2"),
            ],
            [],
            [],
        )
        assert ProcessSpecEnvOverlay.objects.count() == 2
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1

        assert ProcessSpecEnvOverlay.objects.get(proc_spec=proc_web, environment_name="prod").target_replicas == 2
        assert ProcessSpecEnvOverlay.objects.get(proc_spec=proc_celery, environment_name="prod").target_replicas == 2

    def test_only_res_quota(self, bk_module, proc_web, proc_celery):
        assert ProcessSpecEnvOverlay.objects.count() == 2

        ret = sync_proc_env_overlays(
            bk_module,
            [],
            [
                ResQuotaOverlay(env_name="prod", process="web", plan=ResQuotaPlan.P_4C4G),
                ResQuotaOverlay(env_name="prod", process="worker", plan=ResQuotaPlan.P_4C4G),
            ],
            [],
        )
        assert ProcessSpecEnvOverlay.objects.count() == 2
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1

        assert (
            ProcessSpecEnvOverlay.objects.get(proc_spec=proc_web, environment_name="prod").plan_name
            == ResQuotaPlan.P_4C4G
        )
        assert (
            ProcessSpecEnvOverlay.objects.get(proc_spec=proc_celery, environment_name="prod").plan_name
            == ResQuotaPlan.P_4C4G
        )

    def test_only_autoscaling(self, bk_module, proc_web, proc_celery):
        assert ProcessSpecEnvOverlay.objects.count() == 2

        ret = sync_proc_env_overlays(
            bk_module,
            [],
            [],
            [
                AutoscalingOverlay(env_name="prod", process="web", min_replicas=1, max_replicas=2, policy="default"),
                AutoscalingOverlay(
                    env_name="prod", process="worker", min_replicas=2, max_replicas=5, policy="default"
                ),
            ],
        )
        assert ProcessSpecEnvOverlay.objects.count() == 2
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1

        assert ProcessSpecEnvOverlay.objects.get(proc_spec=proc_web, environment_name="prod").autoscaling
        assert ProcessSpecEnvOverlay.objects.get(
            proc_spec=proc_web, environment_name="prod"
        ).scaling_config == AutoscalingConfig(min_replicas=1, max_replicas=2, policy="default")

        assert ProcessSpecEnvOverlay.objects.get(proc_spec=proc_celery, environment_name="prod").autoscaling
        assert ProcessSpecEnvOverlay.objects.get(
            proc_spec=proc_celery, environment_name="prod"
        ).scaling_config == AutoscalingConfig(min_replicas=2, max_replicas=5, policy="default")

    def test_integrated(self, bk_module, proc_web, proc_celery):
        assert ProcessSpecEnvOverlay.objects.count() == 2

        ret = sync_proc_env_overlays(
            bk_module,
            [ReplicasOverlay(env_name="prod", process="web", count="5")],
            [ResQuotaOverlay(env_name="prod", process="web", plan=ResQuotaPlan.P_4C4G)],
            [AutoscalingOverlay(env_name="prod", process="worker", min_replicas=1, max_replicas=2, policy="default")],
        )
        assert ProcessSpecEnvOverlay.objects.count() == 2
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1
