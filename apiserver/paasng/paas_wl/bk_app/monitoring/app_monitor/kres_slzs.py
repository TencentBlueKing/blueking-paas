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

from typing import TYPE_CHECKING, Dict, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer

from .entities import Endpoint, ServiceSelector

if TYPE_CHECKING:
    from paas_wl.bk_app.monitoring.app_monitor.kres_entities import ServiceMonitor


class ServiceMonitorDeserializer(AppEntityDeserializer["ServiceMonitor"]):
    api_version = "monitoring.coreos.com/v1"

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "ServiceMonitor":
        spec = kube_data.to_dict()["spec"]
        endpoint = spec["endpoints"][0]
        return self.entity_type(
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


class ServiceMonitorSerializer(AppEntitySerializer["ServiceMonitor"]):
    api_version = "monitoring.coreos.com/v1"

    def serialize(self, obj: "ServiceMonitor", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
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
