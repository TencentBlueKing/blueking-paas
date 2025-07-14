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

import logging
from pathlib import Path
from unittest import mock

import pytest
import yaml
from django_dynamic_fixture import G
from dynaconf.utils.parse_conf import parse_conf_data
from kubernetes.client.exceptions import ApiException

from paas_wl.bk_app.applications.managers import get_metadata
from paas_wl.bk_app.monitoring.app_monitor import constants
from paas_wl.bk_app.monitoring.app_monitor.managers import build_service_monitor, service_monitor_kmodel
from paas_wl.bk_app.monitoring.app_monitor.models import AppMetricsMonitor
from paas_wl.bk_app.monitoring.app_monitor.shim import make_bk_monitor_controller
from paas_wl.infras.resources.base.kres import KCustomResourceDefinition
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])
logger = logging.getLogger(__name__)


class TestBuilder:
    @pytest.fixture()
    def builtin_relabelings(self, bk_stag_wl_app):
        metadata = get_metadata(bk_stag_wl_app)
        return [
            {
                "action": "replace",
                "targetLabel": "bk_app_code",
                "replacement": metadata.paas_app_code,
            },
            {
                "action": "replace",
                "targetLabel": "bk_module",
                "replacement": metadata.module_name,
            },
            {
                "action": "replace",
                "targetLabel": "bk_env",
                "replacement": metadata.environment,
            },
        ]

    def test_normal(self, bk_stag_wl_app, builtin_relabelings):
        monitor = G(AppMetricsMonitor, port=5000, target_port=5001, app=bk_stag_wl_app)

        svc_monitor = build_service_monitor(monitor)
        assert svc_monitor.endpoint.interval == constants.METRICS_INTERVAL
        assert svc_monitor.endpoint.path == constants.METRICS_PATH
        assert svc_monitor.endpoint.port == constants.METRICS_PORT_NAME
        assert svc_monitor.endpoint.metric_relabelings == builtin_relabelings

    def test_with_extra_field(self, bk_stag_wl_app, settings, builtin_relabelings):
        settings.BKMONITOR_METRIC_RELABELINGS = parse_conf_data(
            '@json [{"action": "replace", "replacement": "bkop.example.com", "targetLabel": "bk_domain"}]'
        )

        monitor = G(AppMetricsMonitor, port=5000, target_port=5001, app=bk_stag_wl_app)
        svc_monitor = build_service_monitor(monitor)

        assert (
            svc_monitor.endpoint.metric_relabelings
            == [{"action": "replace", "replacement": "bkop.example.com", "targetLabel": "bk_domain"}]
            + builtin_relabelings
        )


class TestAppMonitorController:
    @pytest.fixture(autouse=True)
    def _setup(self, settings):
        settings.ENABLE_BK_MONITOR = True

    @pytest.fixture()
    def _setup_crd(self, k8s_client, k8s_version, settings):
        name = "servicemonitors.monitoring.coreos.com"

        if (int(k8s_version.major), int(k8s_version.minor)) <= (1, 16):
            body = yaml.safe_load((Path(__file__).parent / "crd/v1beta1.yaml").read_text())
        else:
            body = yaml.safe_load((Path(__file__).parent / "crd/v1.yaml").read_text())

        try:
            KCustomResourceDefinition(k8s_client).create_or_update(name, body=body)
        except ValueError as e:
            logger.warning("Unknown Exception raise from k8s client, but should be ignored. Detail: %s", e)
        except ApiException as e:
            if e.status == 409:
                # CRD 已存在, 忽略
                pass

        yield
        KCustomResourceDefinition(k8s_client).delete(name)

    @pytest.fixture()
    def monitor(self, bk_stag_wl_app):
        return G(AppMetricsMonitor, port=5000, target_port=5001, app=bk_stag_wl_app)

    @pytest.mark.usefixtures("_setup_crd")
    @pytest.mark.auto_create_ns
    def test_normal(self, monitor, bk_stag_wl_app):
        controller = make_bk_monitor_controller(bk_stag_wl_app)
        assert controller.app_monitor is not None
        controller.create_or_patch()

        assert service_monitor_kmodel.get(bk_stag_wl_app, build_service_monitor(controller.app_monitor).name)
        with mock.patch("paas_wl.bk_app.monitoring.app_monitor.managers.service_monitor_kmodel.update") as mocked:
            controller.create_or_patch()
            assert not mocked.called

        controller.remove()
        with pytest.raises(AppEntityNotFound):
            service_monitor_kmodel.get(bk_stag_wl_app, build_service_monitor(controller.app_monitor).name)

    def test_no_monitor(self, bk_stag_wl_app):
        controller = make_bk_monitor_controller(bk_stag_wl_app)
        with mock.patch("paas_wl.bk_app.monitoring.app_monitor.managers.service_monitor_kmodel") as mocked:
            assert controller.app_monitor is None
            controller.create_or_patch()
            assert not mocked.upsert.called

    def test_disable(self, monitor, bk_stag_wl_app):
        monitor.disable()
        controller = make_bk_monitor_controller(bk_stag_wl_app)
        with mock.patch("paas_wl.bk_app.monitoring.app_monitor.managers.service_monitor_kmodel") as mocked:
            assert controller.app_monitor is not None
            controller.create_or_patch()
            assert not mocked.upsert.called

    def test_global_disable(self, monitor, bk_stag_wl_app, settings):
        settings.ENABLE_BK_MONITOR = False
        controller = make_bk_monitor_controller(bk_stag_wl_app)
        with mock.patch("paas_wl.bk_app.monitoring.app_monitor.managers.service_monitor_kmodel") as mocked:
            controller.create_or_patch()
            assert not mocked.upsert.called
