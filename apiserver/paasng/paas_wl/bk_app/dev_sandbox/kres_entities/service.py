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
from typing import List

from paas_wl.bk_app.dev_sandbox.conf import get_network_configs
from paas_wl.bk_app.dev_sandbox.entities import ServicePortPair
from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox
from paas_wl.bk_app.dev_sandbox.kres_slzs import DevSandboxServiceDeserializer, DevSandboxServiceSerializer
from paas_wl.bk_app.dev_sandbox.names import get_dev_sandbox_service_name
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity


@dataclass
class DevSandboxService(AppEntity):
    ports: List[ServicePortPair]

    class Meta:
        kres_class = kres.KService
        serializer = DevSandboxServiceSerializer
        deserializer = DevSandboxServiceDeserializer

    @classmethod
    def create(cls, dev_sandbox: DevSandbox) -> "DevSandboxService":
        svc_name = get_dev_sandbox_service_name(dev_sandbox.app)

        ports = [
            ServicePortPair(
                name=cfg.svc_port_name,
                port=cfg.port,
                target_port=cfg.target_port,
            )
            for cfg in get_network_configs(dev_sandbox)
        ]
        return cls(app=dev_sandbox.app, name=svc_name, ports=ports)
