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

from paas_wl.bk_app.processes.models import ProcessSpec
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.constants import ResQuotaPlan
from paasng.platform.bkapp_model.entities import (
    AutoscalingConfig,
    AutoscalingOverlay,
    ReplicasOverlay,
    ResQuotaOverlay,
)
from paasng.platform.bkapp_model.entities_syncer import (
    clean_empty_overlays,
    sync_env_overlays_autoscalings,
    sync_env_overlays_replicas,
    sync_env_overlays_res_quotas,
)
from paasng.platform.bkapp_model.models import ProcessSpecEnvOverlay
from paasng.utils.structure import NOTSET

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _setup(bk_module, proc_web, proc_celery):
    G(
        ProcessSpecEnvOverlay,
        proc_spec=proc_web,
        environment_name="stag",
        target_replicas=4,
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
    # Set the record to be manged by APP_DESC
    for proc, env in [(proc_web.name, "stag"), (proc_celery.name, "prod")]:
        fieldmgr.FieldManager(bk_module, fieldmgr.f_overlay_replicas(proc, env)).set(fieldmgr.FieldMgrName.APP_DESC)
        fieldmgr.FieldManager(bk_module, fieldmgr.f_overlay_res_quotas(proc, env)).set(fieldmgr.FieldMgrName.APP_DESC)
        fieldmgr.FieldManager(bk_module, fieldmgr.f_overlay_autoscaling(proc, env)).set(fieldmgr.FieldMgrName.APP_DESC)


class Test__sync_env_overlays_replicas:
    def test_integrated(self, bk_module, proc_web, proc_celery):
        ret = sync_env_overlays_replicas(
            bk_module,
            [
                ReplicasOverlay(env_name="prod", process="web", count=2),
                ReplicasOverlay(env_name="prod", process="worker", count=2),
            ],
            manager=fieldmgr.FieldMgrName.APP_DESC,
        )
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1

        assert get_overlay_obj(proc_web, "prod").target_replicas == 2
        assert get_overlay_obj(proc_celery, "prod").target_replicas == 2
        assert get_overlay_obj(proc_web, "stag").target_replicas is None

        # Set "web" process's field to be manged by a different manager and check if
        # the record should stay intact when getting an `NOTSET` input.
        fieldmgr.FieldManager(bk_module, fieldmgr.f_overlay_replicas(proc_web.name, "prod")).set(
            fieldmgr.FieldMgrName.WEB_FORM
        )
        sync_env_overlays_replicas(bk_module, NOTSET, manager=fieldmgr.FieldMgrName.APP_DESC)
        assert get_overlay_obj(proc_web, "prod").target_replicas == 2
        assert get_overlay_obj(proc_celery, "prod").target_replicas is None
        assert get_overlay_obj(proc_web, "stag").target_replicas is None

        # Manually pass an empty list should reset all records
        sync_env_overlays_replicas(bk_module, [], manager=fieldmgr.FieldMgrName.APP_DESC)
        assert get_overlay_obj(proc_web, "prod").target_replicas is None

    def test_clean_empty(self, bk_module):
        old_cnt = ProcessSpecEnvOverlay.objects.count()
        sync_env_overlays_replicas(
            bk_module,
            [ReplicasOverlay(env_name="prod", process="web", count=2)],
            manager=fieldmgr.FieldMgrName.APP_DESC,
        )
        assert ProcessSpecEnvOverlay.objects.count() == old_cnt + 1

        # This should reset the "target_replicas" of all records to None
        sync_env_overlays_replicas(bk_module, [], manager=fieldmgr.FieldMgrName.APP_DESC)
        clean_empty_overlays(bk_module)
        assert ProcessSpecEnvOverlay.objects.count() == old_cnt


class Test__sync_env_overlays_res_quotas:
    def test_normal(self, bk_module, proc_web, proc_celery):
        ret = sync_env_overlays_res_quotas(
            bk_module,
            [
                ResQuotaOverlay(env_name="prod", process="web", plan=ResQuotaPlan.P_4C4G),
                ResQuotaOverlay(env_name="prod", process="worker", plan=ResQuotaPlan.P_4C4G),
            ],
            manager=fieldmgr.FieldMgrName.APP_DESC,
        )
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1

        assert get_overlay_obj(proc_web, "prod").plan_name == ResQuotaPlan.P_4C4G
        assert get_overlay_obj(proc_celery, "prod").plan_name == ResQuotaPlan.P_4C4G
        assert get_overlay_obj(proc_web, "stag").plan_name is None


class Test__sync_env_overlays_autoscalings:
    def test_normal(self, bk_module, proc_web, proc_celery):
        ret = sync_env_overlays_autoscalings(
            bk_module,
            [
                AutoscalingOverlay(env_name="prod", process="web", min_replicas=1, max_replicas=2, policy="default"),
                AutoscalingOverlay(
                    env_name="prod", process="worker", min_replicas=2, max_replicas=5, policy="default"
                ),
            ],
            manager=fieldmgr.FieldMgrName.APP_DESC,
        )
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1

        assert get_overlay_obj(proc_web, "prod").autoscaling
        assert get_overlay_obj(proc_web, "prod").scaling_config == AutoscalingConfig(
            min_replicas=1, max_replicas=2, policy="default"
        )

        assert get_overlay_obj(proc_celery, "prod").autoscaling
        assert get_overlay_obj(proc_celery, "prod").scaling_config == AutoscalingConfig(
            min_replicas=2, max_replicas=5, policy="default"
        )

        assert get_overlay_obj(proc_web, "stag").autoscaling is None
        assert get_overlay_obj(proc_web, "stag").scaling_config is None


def get_overlay_obj(proc_spec: ProcessSpec, env_name: str):
    """A helper function to get the overlay object."""
    return ProcessSpecEnvOverlay.objects.get(proc_spec=proc_spec, environment_name=env_name)
