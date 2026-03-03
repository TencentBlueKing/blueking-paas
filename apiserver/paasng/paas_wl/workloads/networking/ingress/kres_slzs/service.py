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

from typing import TYPE_CHECKING, Any, Dict

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.managers import get_metadata
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.processes.constants import PROCESS_NAME_KEY
from paas_wl.core.resource import get_process_selector
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer
from paas_wl.workloads.networking.ingress.entities import PServicePortPair

if TYPE_CHECKING:
    from paas_wl.workloads.networking.ingress.kres_entities.service import ProcessService


class ProcessServiceSerializer(AppEntitySerializer["ProcessService"]):
    """Serializer for ProcessService"""

    def get_kube_annotations(self, service: "ProcessService") -> Dict:
        return {"process_type": service.process_type}

    def get_kube_labels(self, service: "ProcessService") -> Dict:
        metadata = get_metadata(service.app)
        return {
            "name": service.name,
            # Note: 与蓝鲸监控协商新增的 label
            # bk_app_code 用于过滤应用
            "monitoring.bk.tencent.com/bk_app_code": metadata.paas_app_code,
            # module_name 用于平台过滤模块
            "monitoring.bk.tencent.com/module_name": metadata.module_name,
            # environment 用于平台过滤运行环境
            "monitoring.bk.tencent.com/environment": metadata.environment,
            PROCESS_NAME_KEY: service.process_type,
        }

    def serialize(self, obj: "ProcessService", original_obj=None, **kwargs) -> Dict:
        """Generate a kubernetes resource dict from ProcessService

        :param original_obj: if given, will update resource_version and other necessary fields
        """
        service = obj
        kube_selector = get_process_selector(service.app, service.process_type)
        body: Dict[str, Any] = {
            "metadata": {
                "name": service.name,
                "annotations": self.get_kube_annotations(service),
                "namespace": service.app.namespace,
                "labels": self.get_kube_labels(service),
            },
            "spec": {
                "ports": [
                    {"name": p.name, "port": p.port, "targetPort": p.target_port, "protocol": p.protocol}
                    for p in service.ports
                ],
                "selector": kube_selector,
            },
            "api_version": "v1",
            "kind": "Service",
        }

        if original_obj:
            body["metadata"]["resourceVersion"] = original_obj.metadata.resourceVersion
            # Must provide same ClusterIP property or apiserver will complain
            body["spec"]["clusterIP"] = original_obj.spec.clusterIP
        return body


class ProcessServiceDeserializer(AppEntityDeserializer["ProcessService", "WlApp"]):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "ProcessService":
        """Generate a ProcessService object from kubernetes resource"""
        res_name = kube_data.metadata.name

        # 优先处理云原生应用, 如 labels: {'bkapp.paas.bk.tencent.com/process-name': 'web'}
        labels = kube_data.metadata.get("labels", {})
        process_type = labels.get(PROCESS_NAME_KEY)

        if not process_type:
            annotations = kube_data.metadata.get("annotations", {})
            try:
                process_type = annotations["process_type"]
            except KeyError:
                # Backward-compatibility
                process_type = self.extract_process_type_from_name(app, res_name)

        ports = [
            PServicePortPair(name=p.name, protocol=p.protocol, port=p.port, target_port=p.targetPort)
            for p in kube_data.spec.ports
        ]
        return self.entity_type(name=res_name, app=app, process_type=process_type, ports=ports)

    @staticmethod
    def extract_process_type_from_name(app: WlApp, name: str) -> str:
        """Try to extract the process_type from service name"""
        default_prefix = f"{app.region}-{app.scheduler_safe_name}"
        if not name.startswith(default_prefix):
            raise ValueError("Unable to extract process_type")
        return name[len(default_prefix) + 1 :]
