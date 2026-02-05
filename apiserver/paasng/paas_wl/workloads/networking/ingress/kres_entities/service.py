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

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity, AppEntityManager
from paas_wl.workloads.networking.ingress.entities import PServicePortPair
from paas_wl.workloads.networking.ingress.kres_slzs.service import ProcessServiceDeserializer, ProcessServiceSerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models.app import WlApp


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


service_kmodel: AppEntityManager[ProcessService, "WlApp"] = AppEntityManager(ProcessService)
