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

"""controller 参考 paas_wl.bk_app.monitoring.app_monitor.manager 实现. 不直接复用(比如补一个 CNativeMonitorController)的
主要原因是会导致 paas_wl 反向依赖 paasng 里的 ObservabilityConfig model
"""

import logging

from django.conf import settings

from paas_wl.bk_app.monitoring.app_monitor.entities import Endpoint, ServiceSelector
from paas_wl.bk_app.monitoring.app_monitor.kres_entities import ServiceMonitor
from paas_wl.bk_app.monitoring.app_monitor.managers import service_monitor_kmodel
from paas_wl.bk_app.processes.constants import PROCESS_NAME_KEY
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.entities.observability import Metric
from paasng.platform.bkapp_model.models import ObservabilityConfig

logger = logging.getLogger(__name__)


def make_svc_monitor_controller(env: ModuleEnvironment):
    if not settings.ENABLE_BK_MONITOR:
        logger.warning("BKMonitor is not ready, skip apply ServiceMonitor")
        return NullController()
    else:
        return ServiceMonitorController(env)


class ServiceMonitorController:
    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.wl_app = env.wl_app
        self.module = env.module

    def sync(self):
        """对比 ObservabilityConfig 中的 monitoring 和 last_monitoring, 将新增(或更新)的 metric 采集规则转换成
        ServiceMonitor 下发到集群中, 同时删除废弃的 ServiceMonitor"""

        observability: ObservabilityConfig = self.module.observability
        if not observability:
            return

        # 删除废弃的 ServiceMonitor
        deleted_metric_processes = set(observability.last_metric_processes) - set(observability.metric_processes)
        for process in deleted_metric_processes:
            self._delete(process)

        if not observability.monitoring or not observability.monitoring.metrics:
            return

        # 新增或更新 ServiceMonitor
        for metric in observability.monitoring.metrics:
            self._upsert(metric)

    def _upsert(self, metric: Metric):
        """由 metric 创建或更新 ServiceMonitor"""
        svc_monitor = self._build_service_monitor(metric)
        try:
            existed_service_monitor = service_monitor_kmodel.get(app=svc_monitor.app, name=svc_monitor.name)
        except AppEntityNotFound:
            service_monitor_kmodel.save(svc_monitor)
            return

        if existed_service_monitor != svc_monitor:
            # DynamicClient 默认使用 strategic-merge-patch, CRD 不支持, 因此需要使用 merge-patch
            service_monitor_kmodel.update(
                svc_monitor, update_method="patch", content_type="application/merge-patch+json"
            )

    def _delete(self, process: str):
        """删除与 process 关联的 ServiceMonitor"""
        try:
            instance = service_monitor_kmodel.get(app=self.wl_app, name=self._build_service_monitor_name(process))
        except AppEntityNotFound:
            return

        service_monitor_kmodel.delete_by_name(app=self.wl_app, name=instance.name)

    def _build_service_monitor_name(self, process: str) -> str:
        return f"{self.wl_app.scheduler_safe_name}--{process}"

    def _build_service_monitor(self, metric: Metric) -> ServiceMonitor:
        app_code = self.env.application.code
        module_name = self.module.name

        return ServiceMonitor(
            app=self.wl_app,
            name=self._build_service_monitor_name(metric.process),
            endpoint=Endpoint(
                path=metric.path,
                port=metric.service_name,
                params=metric.params,
                metric_relabelings=settings.BKMONITOR_METRIC_RELABELINGS
                + [
                    {
                        "action": "replace",
                        "targetLabel": "bk_app_code",
                        "replacement": app_code,
                    },
                    {
                        "action": "replace",
                        "targetLabel": "bk_module",
                        "replacement": module_name,
                    },
                    {
                        "action": "replace",
                        "targetLabel": "bk_env",
                        "replacement": self.env.environment,
                    },
                ],
            ),
            selector=ServiceSelector(
                # 以下 labels 在 operator 创建 service 时注入
                matchLabels={
                    # 蓝鲸监控根据 bk_app_code label 识别应用
                    "monitoring.bk.tencent.com/bk_app_code": app_code,
                    "monitoring.bk.tencent.com/module_name": module_name,
                    PROCESS_NAME_KEY: metric.process,
                }
            ),
            match_namespaces=[self.wl_app.namespace],
        )


class NullController:
    def sync(self):
        """同步 ServiceMonitor"""
