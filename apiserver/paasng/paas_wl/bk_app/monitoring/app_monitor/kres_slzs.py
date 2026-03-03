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

from typing import TYPE_CHECKING, Dict, List, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer

from .entities import Endpoint, ServiceSelector

if TYPE_CHECKING:
    from paas_wl.bk_app.monitoring.app_monitor.kres_entities import ServiceMonitor


class ServiceMonitorDeserializer(AppEntityDeserializer["ServiceMonitor", "WlApp"]):
    api_version = "monitoring.coreos.com/v1"

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "ServiceMonitor":
        spec = kube_data.to_dict()["spec"]
        ep_spec = spec["endpoints"][0]

        endpoint = Endpoint(
            interval=ep_spec["interval"],
            path=ep_spec["path"],
            port=ep_spec["port"],
            metric_relabelings=ep_spec["metricRelabelings"],
        )

        if params := ep_spec.get("params"):
            # params is Dict[str, List[str]] type.
            # see https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/api.md#endpoint
            endpoint.params = {k: v[0] for k, v in params.items()}

        return self.entity_type(
            app=app,
            name=kube_data["metadata"]["name"],
            endpoint=endpoint,
            selector=ServiceSelector(matchLabels=spec["selector"]["matchLabels"]),
            match_namespaces=spec["namespaceSelector"]["matchNames"],
        )


class ServiceMonitorSerializer(AppEntitySerializer["ServiceMonitor"]):
    api_version = "monitoring.coreos.com/v1"

    def serialize(self, obj: "ServiceMonitor", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        """
        serialize to ServiceMonitor described in
        https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/api.md
        """
        return {
            "apiVersion": self.get_apiversion(),
            "kind": "ServiceMonitor",
            "metadata": {
                "name": obj.name,
            },
            "spec": {
                "namespaceSelector": {"matchNames": obj.match_namespaces},
                "endpoints": self._construct_endpoints_spec(obj.endpoint),
                "selector": {"matchLabels": obj.selector.matchLabels},
            },
        }

    def _construct_endpoints_spec(self, ep: Endpoint) -> List[Dict]:
        """
        construct endpoints spec, see
        https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/api.md#endpoint
        """
        ep_spec = {
            "interval": ep.interval,
            "path": ep.path,
            "port": ep.port,
            "metricRelabelings": ep.metric_relabelings,
        }

        if ep.params:
            # params type is discussed in https://github.com/prometheus-operator/prometheus-operator/issues/2586
            ep_spec["params"] = {k: [v] for k, v in ep.params.items()}  # type: ignore

        return [ep_spec]
