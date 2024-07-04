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

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppProcess, HTTPGetAction, Probe, ProbeSet, TCPSocketAction
from paasng.platform.bkapp_model.importer.processes import import_processes
from paasng.platform.bkapp_model.models import ModuleProcessSpec

pytestmark = pytest.mark.django_db


class Test__import_processes:
    def test_integrated(self, bk_module, proc_web, proc_celery):
        assert ModuleProcessSpec.objects.filter(module=bk_module).count() == 2

        ret = import_processes(
            bk_module,
            [
                BkAppProcess(
                    name="web",
                    replicas=1,
                    command=["./start.sh"],
                    probes=ProbeSet(
                        liveness=Probe(
                            httpGet=HTTPGetAction(port="${PORT}", path="/healthz"),
                            initialDelaySeconds=30,
                            timeoutSeconds=5,
                            periodSeconds=5,
                            successThreshold=1,
                            failureThreshold=3,
                        ),
                        readiness=Probe(tcpSocket=TCPSocketAction(port=5000)),
                    ),
                ),
                BkAppProcess(name="sleep", replicas=1, command=["bash"], args=["-c", "100"]),
            ],
        )
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1

        specs = ModuleProcessSpec.objects.filter(module=bk_module, name=proc_web.name)
        assert specs.count() == 1

        spec = specs.first()
        assert spec.probes.liveness.http_get.port == "${PORT}"
        assert spec.probes.liveness.initial_delay_seconds == 30
        assert spec.probes.liveness.period_seconds == 5
        assert spec.probes.readiness.tcp_socket.port == 5000
