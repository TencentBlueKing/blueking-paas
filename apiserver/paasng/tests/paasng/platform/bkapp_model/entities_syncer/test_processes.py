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

from paasng.platform.bkapp_model.entities import (
    AutoscalingConfig,
    HTTPGetAction,
    Probe,
    ProbeSet,
    Process,
    TCPSocketAction,
)
from paasng.platform.bkapp_model.entities_syncer import sync_processes
from paasng.platform.bkapp_model.models import ModuleProcessSpec

pytestmark = pytest.mark.django_db


class Test__sync_processes:
    def test_integrated(self, bk_module, proc_web, proc_celery):
        assert ModuleProcessSpec.objects.filter(module=bk_module).count() == 2

        ret = sync_processes(
            bk_module,
            [
                Process(
                    name=proc_web.name,
                    replicas=1,
                    command=["./start.sh"],
                    res_quota_plan="4C1G",
                    target_port=30000,
                    probes=ProbeSet(
                        liveness=Probe(
                            http_get=HTTPGetAction(port="${PORT}", path="/healthz"),
                            initial_delay_seconds=30,
                            timeout_seconds=5,
                            period_seconds=5,
                            success_threshold=1,
                            failure_threshold=3,
                        ),
                        readiness=Probe(tcp_socket=TCPSocketAction(port=30000)),
                    ),
                ),
                Process(
                    name="sleep",
                    replicas=1,
                    command=["bash"],
                    res_quota_plan="4C2G",
                    args=["-c", "100"],
                    proc_command="sleep 100",
                    autoscaling=AutoscalingConfig(min_replicas=2, max_replicas=10, policy="default"),
                ),
            ],
        )
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1

        assert ModuleProcessSpec.objects.filter(module=bk_module).count() == 2

        specs = ModuleProcessSpec.objects.filter(module=bk_module, name=proc_web.name)
        assert specs.count() == 1

        spec = specs.first()
        assert spec.port == 30000
        assert spec.probes.liveness.http_get.port == "${PORT}"
        assert spec.probes.liveness.initial_delay_seconds == 30
        assert spec.probes.liveness.period_seconds == 5
        assert spec.probes.readiness.tcp_socket.port == 30000
        assert spec.plan_name == "4C1G"

        spec = ModuleProcessSpec.objects.get(module=bk_module, name="sleep")
        assert spec.proc_command == "sleep 100"
        assert spec.command is None
        assert spec.target_replicas == 1
        assert spec.scaling_config.max_replicas == 10
        assert spec.scaling_config.min_replicas == 2
        assert spec.plan_name == "4C2G"
