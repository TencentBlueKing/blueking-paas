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

from unittest import mock

import pytest
from django_dynamic_fixture import G

from paas_wl.bk_app.monitoring.app_monitor.kres_entities import Endpoint, ServiceMonitor, ServiceSelector
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paasng.misc.monitoring.monitor.service_monitor.controller import ServiceMonitorController
from paasng.platform.bkapp_model.models import ObservabilityConfig

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.usefixtures("_with_wl_apps"),
]


class StubServiceMonitorKModel:
    def get(self, *args, **kwargs):
        ...

    def update(self, *args, **kwargs):
        ...

    def delete(self, *args, **kwargs):
        ...


class TestServiceMonitorController:
    def test_init_sync(self, bk_stag_env):
        G(
            ObservabilityConfig,
            module=bk_stag_env.module,
            monitoring={
                "metrics": [{"process": "web", "service_name": "metric", "path": "/metric", "params": {"foo": "bar"}}]
            },
        )

        with mock.patch(
            "paasng.misc.monitoring.monitor.service_monitor.controller.service_monitor_kmodel",
        ) as mocked:
            mocked.get.side_effect = AppEntityNotFound()

            controller = ServiceMonitorController(env=bk_stag_env)
            controller.sync()

            mocked.get.assert_called_with(
                app=bk_stag_env.wl_app, name=bk_stag_env.wl_app.scheduler_safe_name + "--web"
            )
            mocked.save.assert_called()
            assert mocked.update.call_count == 0
            assert mocked.delete_by_name.call_count == 0

    def test_sync_with_different_process(self, bk_stag_env):
        G(
            ObservabilityConfig,
            module=bk_stag_env.module,
            monitoring={
                "metrics": [{"process": "web", "service_name": "metric", "path": "/metric", "params": {"foo": "bar"}}]
            },
            last_monitoring={"metrics": [{"process": "backend", "service_name": "api", "path": "/api/metric"}]},
        )

        with mock.patch(
            "paasng.misc.monitoring.monitor.service_monitor.controller.service_monitor_kmodel",
        ) as mocked:

            def get_instance(app, name):
                if name == bk_stag_env.wl_app.scheduler_safe_name + "--backend":
                    return ServiceMonitor(
                        app=app,
                        name=name,
                        endpoint=Endpoint(path="/api/metric", port="api"),
                        selector=ServiceSelector(matchLabels={}),
                        match_namespaces=[app.namespace],
                    )
                raise AppEntityNotFound()

            mocked.get.side_effect = get_instance

            controller = ServiceMonitorController(env=bk_stag_env)
            controller.sync()

            mocked.delete_by_name.assert_called_with(
                app=bk_stag_env.wl_app, name=bk_stag_env.wl_app.scheduler_safe_name + "--backend"
            )
            assert mocked.get.call_count == 2
            mocked.save.assert_called()
            assert mocked.update.call_count == 0
            assert mocked.delete.call_count == 0

    def test_sync_with_same_process(self, bk_stag_env):
        G(
            ObservabilityConfig,
            module=bk_stag_env.module,
            monitoring={
                "metrics": [{"process": "web", "service_name": "metric", "path": "/metric", "params": {"foo": "bar"}}]
            },
            last_monitoring={"metrics": [{"process": "web", "service_name": "metric", "path": "/api/metric"}]},
        )

        with mock.patch(
            "paasng.misc.monitoring.monitor.service_monitor.controller.service_monitor_kmodel",
        ) as mocked:
            wl_app = bk_stag_env.wl_app
            mocked.get.return_value = ServiceMonitor(
                app=wl_app,
                name=wl_app.scheduler_safe_name + "--web",
                endpoint=Endpoint(path="/api/metric", port="api"),
                selector=ServiceSelector(matchLabels={}),
                match_namespaces=[wl_app.namespace],
            )

            controller = ServiceMonitorController(env=bk_stag_env)
            controller.sync()

            assert mocked.delete_by_name.call_count == 0
            assert mocked.get.call_count == 1
            assert mocked.update.call_count == 1
