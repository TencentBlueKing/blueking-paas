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

from django.conf import settings

from paasng.platform.bkapp_model.entities import ProbeSet, ProcService


class TestSanitizePortPlaceholder:
    def test_proc_service(self):
        proc_service = ProcService(**{"target_port": "${PORT}", "name": "web"})
        assert proc_service.sanitize_port_placeholder().target_port == settings.CONTAINER_PORT

        proc_service = ProcService(**{"target_port": 8080, "name": "web"})
        assert proc_service.sanitize_port_placeholder().target_port == 8080

    def test_probes(self):
        probes = ProbeSet(
            **{
                "liveness": {"http_get": {"port": "${PORT}"}},
                "readiness": {"tcp_socket": {"port": "${PORT}"}},
                "startup": {"http_get": {"port": 8000}},
            }
        )
        sanitized_probes = probes.sanitize_port_placeholder()
        assert sanitized_probes.liveness.http_get.port == settings.CONTAINER_PORT
        assert sanitized_probes.readiness.tcp_socket.port == settings.CONTAINER_PORT
        assert sanitized_probes.startup.http_get.port == 8000
