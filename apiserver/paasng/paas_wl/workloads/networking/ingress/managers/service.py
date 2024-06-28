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
from typing import Optional

from django.conf import settings

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.networking.ingress.entities import PServicePortPair
from paas_wl.workloads.networking.ingress.kres_entities.service import ProcessService, service_kmodel
from paas_wl.workloads.networking.ingress.managers import AppDefaultIngresses
from paas_wl.workloads.networking.ingress.utils import make_service_name

logger = logging.getLogger(__name__)


def build_process_service(app: WlApp, process_type: str) -> ProcessService:
    """Generate the desired ProcessService object"""
    name = make_service_name(app, process_type)
    ports = [PServicePortPair(name="http", port=80, target_port=settings.CONTAINER_PORT)]

    return ProcessService(
        app=app,
        name=name,
        process_type=process_type,
        ports=ports,
    )


class ProcDefaultServices:
    """Maintains default service and ingress rules for each app process(k8s side)

    :param monitor_port: The port for monitoring functionality.
    """

    def __init__(self, app: WlApp, process_type: str, monitor_port: Optional[PServicePortPair] = None):
        self.process_type = process_type
        self.app = app
        self.monitor_port = monitor_port

    def create_or_patch(self):
        """Create or patch service / (ingress) resources"""
        service = build_process_service(self.app, self.process_type)
        if self.monitor_port:
            service.ports.append(self.monitor_port)

        try:
            existed_service = service_kmodel.get(self.app, service.name)
        except AppEntityNotFound:
            service_kmodel.create(service)
        else:
            # Add metrics service port if not exists.
            if self.monitor_port and not existed_service.has_port(self.monitor_port.name):
                existed_service.ports.append(self.monitor_port)
                service_kmodel.update(existed_service)

        if self.should_create_ingress():
            AppDefaultIngresses(self.app).sync_ignore_empty(default_service_name=service.name)

    def remove(self):
        """Remove service / (ingress) resources"""
        service_name = make_service_name(self.app, self.process_type)
        service_kmodel.delete_by_name(self.app, service_name)
        AppDefaultIngresses(self.app).delete_if_service_matches(service_name)

    def should_create_ingress(self):
        """whether to create an ingress rule or not"""
        # TODO: 由 ProcessSpec 模型控制是否创建 ingress
        return self.process_type == "web"
