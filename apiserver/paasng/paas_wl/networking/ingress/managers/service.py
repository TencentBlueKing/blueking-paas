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

from django.conf import settings

from paas_wl.monitoring.app_monitor.utils import build_monitor_port
from paas_wl.networking.ingress.entities.service import ProcessService, PServicePortPair, service_kmodel
from paas_wl.networking.ingress.managers import AppDefaultIngresses
from paas_wl.networking.ingress.utils import make_service_name
from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.processes.models import Process

logger = logging.getLogger(__name__)


def build_process_service(app: WlApp, process_type: str) -> ProcessService:
    """Generate the desired ProcessService object"""
    name = make_service_name(app, process_type)
    ports = [PServicePortPair(name="http", port=80, target_port=settings.CONTAINER_PORT)]
    monitor_port = build_monitor_port(app)
    if monitor_port:
        ports.append(monitor_port)

    return ProcessService(
        app=app,
        name=name,
        process_type=process_type,
        ports=ports,
    )


class ProcDefaultServices:
    """Maintains default service and ingress rules for each app process(k8s side)"""

    def __init__(self, process: Process):
        self.process = process
        self.app = process.app

    def create_or_patch(self):
        """Create or patch service / (ingress) resources"""
        service = build_process_service(self.app, self.process.type)
        try:
            service = service_kmodel.get(self.app, service.name)
        except AppEntityNotFound:
            service_kmodel.create(service)
        else:
            # Add metrics service port if not exists.
            monitor_port = build_monitor_port(self.app)
            if monitor_port and not service.has_port(monitor_port.name):
                service.ports.append(monitor_port)
                service_kmodel.update(service)

        if self.should_create_ingress():
            AppDefaultIngresses(self.app).sync_ignore_empty(default_service_name=service.name)

    def remove(self):
        """Remove service / (ingress) resources"""
        service_name = make_service_name(self.app, self.process.type)
        service_kmodel.delete_by_name(self.app, service_name)
        AppDefaultIngresses(self.app).delete_if_service_matches(service_name)

    def should_create_ingress(self):
        """whether to create an ingress rule or not"""
        # TODO: 由 ProcessSpec 模型控制是否创建 ingress
        return self.process.type == "web"
