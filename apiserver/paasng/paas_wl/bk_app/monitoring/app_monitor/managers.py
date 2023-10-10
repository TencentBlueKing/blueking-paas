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
from typing import Optional

from django.conf import settings

from paas_wl.bk_app.monitoring.app_monitor import constants
from paas_wl.bk_app.monitoring.app_monitor.entities import Endpoint, ServiceMonitor, ServiceSelector, service_monitor_kmodel
from paas_wl.bk_app.monitoring.app_monitor.models import AppMetricsMonitor
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.applications.models.managers.app_metadata import get_metadata
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound


def build_service_monitor_name(app: WlApp) -> str:
    """Generate the ServiceMonitor name"""
    return app.scheduler_safe_name + "--monitor"


def build_service_monitor(monitor: AppMetricsMonitor) -> ServiceMonitor:
    """Generate the desired ServiceMonitor object

    :return: ServiceMonitor
    """
    metadata = get_metadata(monitor.app)
    metric_relabelings = settings.BKMONITOR_METRIC_RELABELINGS

    return ServiceMonitor(
        app=monitor.app,
        name=build_service_monitor_name(monitor.app),
        endpoint=Endpoint(
            interval=constants.METRICS_INTERVAL,
            path=constants.METRICS_PATH,
            port=constants.METRICS_PORT_NAME,
            metric_relabelings=metric_relabelings
            + [
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
            ],
        ),
        selector=ServiceSelector(
            matchLabels={
                # Note: 与蓝鲸监控协商新增的 label
                "monitoring.bk.tencent.com/bk_app_code": metadata.paas_app_code,
            }
        ),
        match_namespaces=[monitor.app.namespace],
    )


class AppMonitorController:
    app_monitor: Optional[AppMetricsMonitor]

    def __init__(self, app: WlApp):
        self.app = app
        try:
            self.app_monitor = AppMetricsMonitor.objects.get(app=app)
        except AppMetricsMonitor.DoesNotExist:
            self.app_monitor = None

    def create_or_patch(self):
        """创建当前 WlApp 与 ServiceMonitor 的关联关系, 如果 ServiceMonitor 不存在, 则创建."""
        if not self.app_monitor or not self.app_monitor.is_enabled:
            return

        svc_monitor = build_service_monitor(self.app_monitor)
        try:
            existed = service_monitor_kmodel.get(app=svc_monitor.app, name=svc_monitor.name)
        except AppEntityNotFound:
            service_monitor_kmodel.save(svc_monitor)
            return

        if existed != svc_monitor:
            # DynamicClient 默认使用 strategic-merge-patch, CRD 不支持, 因此需要使用 merge-patch
            service_monitor_kmodel.update(
                svc_monitor, update_method='patch', content_type="application/merge-patch+json"
            )

    def remove(self):
        """删除当前 WlApp 与 ServiceMonitor 的关联关系, 如果 ServiceMonitor 只关联当前 WlApp, 则直接删除 ServiceMonitor"""
        if not self.app_monitor:
            return

        try:
            instance = service_monitor_kmodel.get(app=self.app, name=build_service_monitor_name(self.app))
        except AppEntityNotFound:
            return

        service_monitor_kmodel.delete_by_name(app=self.app, name=instance.name)
        self.app_monitor.disable()


class NullController:
    def create_or_patch(self):
        ...

    def remove(self):
        ...
