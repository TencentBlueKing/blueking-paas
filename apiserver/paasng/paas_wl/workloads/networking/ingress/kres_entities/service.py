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
from dataclasses import dataclass
from typing import Any, Dict, List

from attrs import define
from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.applications.models.managers.app_metadata import get_metadata
from paas_wl.bk_app.processes.constants import PROCESS_NAME_KEY
from paas_wl.core.resource import get_process_selector
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import (
    AppEntity,
    AppEntityDeserializer,
    AppEntityManager,
    AppEntitySerializer,
)


class ProcessServiceSerializer(AppEntitySerializer['ProcessService']):
    """Serializer for ProcessService"""

    def get_kube_annotations(self, service: 'ProcessService') -> Dict:
        return {'process_type': service.process_type}

    def get_kube_labels(self, service: 'ProcessService') -> Dict:
        metadata = get_metadata(service.app)
        return {
            "name": service.name,
            # Note: 与蓝鲸监控协商新增的 label
            "monitoring.bk.tencent.com/bk_app_code": metadata.paas_app_code,
            "monitoring.bk.tencent.com/module_name": metadata.module_name,
            "monitoring.bk.tencent.com/environment": metadata.environment,
            PROCESS_NAME_KEY: service.process_type,
        }

    def serialize(self, obj: 'ProcessService', original_obj=None, **kwargs) -> Dict:
        """Generate a kubernetes resource dict from ProcessService

        :param original_obj: if given, will update resource_version and other necessary fields
        """
        assert isinstance(obj, ProcessService), 'obj must be "ProcessService" type'
        service = obj
        kube_selector = get_process_selector(service.app, service.process_type)
        body: Dict[str, Any] = {
            'metadata': {
                'name': service.name,
                'annotations': self.get_kube_annotations(service),
                'namespace': service.app.namespace,
                'labels': self.get_kube_labels(service),
            },
            'spec': {
                'ports': [
                    {"name": p.name, "port": p.port, "targetPort": p.target_port, "protocol": p.protocol}
                    for p in service.ports
                ],
                'selector': kube_selector,
            },
            'api_version': "v1",
            'kind': "Service",
        }

        if original_obj:
            body['metadata']['resourceVersion'] = original_obj.metadata.resourceVersion
            # Must provide same ClusterIP property or apiserver will complain
            body['spec']['clusterIP'] = original_obj.spec.clusterIP
        return body


class ProcessServiceDeserializer(AppEntityDeserializer['ProcessService']):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> 'ProcessService':
        """Generate a ProcessService object from kubernetes resource"""
        res_name = kube_data.metadata.name

        # 优先处理云原生应用, 如 labels: {'bkapp.paas.bk.tencent.com/process-name': 'web'}
        labels = kube_data.metadata.get('labels', {})
        process_type = labels.get(PROCESS_NAME_KEY)

        if not process_type:
            annotations = kube_data.metadata.get('annotations', {})
            try:
                process_type = annotations['process_type']
            except KeyError:
                raise ValueError(f'Unable to extract process_type from process service {res_name}')

        ports = [
            PServicePortPair(name=p.name, protocol=p.protocol, port=p.port, target_port=p.targetPort)
            for p in kube_data.spec.ports
        ]
        return ProcessService(name=res_name, app=app, process_type=process_type, ports=ports)


@define
class PServicePortPair:
    """Service port pair"""

    name: str
    port: int
    target_port: int
    protocol: str = 'TCP'


@dataclass
class ProcessService(AppEntity):
    """Service object for app process, internal service"""

    process_type: str
    ports: List[PServicePortPair]

    def has_port(self, port_name: str) -> bool:
        """return if the Service has any port match given name"""
        return any(port.name == port_name for port in self.ports)

    class Meta:
        kres_class = kres.KService
        deserializer = ProcessServiceDeserializer
        serializer = ProcessServiceSerializer


service_kmodel: AppEntityManager[ProcessService] = AppEntityManager(ProcessService)
