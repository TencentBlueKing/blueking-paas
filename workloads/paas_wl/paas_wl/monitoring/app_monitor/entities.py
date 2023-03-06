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
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.monitoring.app_monitor import constants
from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.base.crd import KServiceMonitor
from paas_wl.resources.kube_res.base import AppEntity, AppEntityDeserializer, AppEntityManager, AppEntitySerializer

logger = logging.getLogger(__name__)


class ServiceMonitorDeserializer(AppEntityDeserializer['ServiceMonitor']):
    api_version = "monitoring.coreos.com/v1"

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> 'ServiceMonitor':
        spec = kube_data.to_dict()["spec"]
        endpoint = spec["endpoints"][0]
        return ServiceMonitor(
            app=app,
            name=kube_data["metadata"]["name"],
            endpoint=Endpoint(
                interval=endpoint["interval"],
                path=endpoint["path"],
                port=endpoint["port"],
                metric_relabelings=endpoint["metricRelabelings"],
            ),
            selector=ServiceSelector(matchLabels=spec["selector"]["matchLabels"]),
            match_namespaces=spec["namespaceSelector"]["matchNames"],
        )


class ServiceMonitorSerializer(AppEntitySerializer['ServiceMonitor']):
    api_version = "monitoring.coreos.com/v1"

    def serialize(self, obj: 'ServiceMonitor', original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        endpoint = obj.endpoint
        return {
            "apiVersion": self.get_apiversion(),
            "kind": "ServiceMonitor",
            "metadata": {
                "name": obj.name,
            },
            "spec": {
                "namespaceSelector": {"matchNames": obj.match_namespaces},
                "endpoints": [
                    {
                        "interval": endpoint.interval,
                        "path": endpoint.path,
                        "port": endpoint.port,
                        "metricRelabelings": endpoint.metric_relabelings,
                    }
                ],
                "selector": {"matchLabels": obj.selector.matchLabels},
            },
        }


@dataclass
class Endpoint:
    # 蓝鲸监控采集 metrics 的间隔
    interval: str = constants.METRICS_INTERVAL
    # SaaS 暴露 metrics 的路径, 根据约定只能是 /metrics
    path: str = constants.METRICS_PATH
    # SaaS 暴露 metrics 的端口名, 根据约定只能是 metrics
    port: str = constants.METRICS_PORT_NAME
    # Metric 重标签配置, 由集群运维负责控制下发
    metric_relabelings: Optional[List[Dict]] = None


@dataclass
class ServiceSelector:
    # matchLabels 用于过滤蓝鲸监控 ServiceMonitor 监听的 Service
    matchLabels: Dict[str, str]


@dataclass
class ServiceMonitor(AppEntity):
    """ServiceMonitor 通过 selector 过滤需要监控的 Service, 并通过访问 endpoint 描述的端口进行数据采集"""

    endpoint: Endpoint
    selector: ServiceSelector
    match_namespaces: List[str]

    class Meta:
        kres_class = KServiceMonitor
        deserializer = ServiceMonitorDeserializer
        serializer = ServiceMonitorSerializer


service_monitor_kmodel: AppEntityManager[ServiceMonitor] = AppEntityManager(ServiceMonitor)
