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

from typing import TYPE_CHECKING, Any, Dict, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.dev_sandbox.entities import ServicePortPair
from paas_wl.bk_app.dev_sandbox.labels import get_dev_sandbox_labels
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandboxService


class DevSandboxServiceSerializer(AppEntitySerializer["DevSandboxService"]):
    def serialize(self, obj: "DevSandboxService", original_obj: Optional[ResourceInstance] = None, **kwargs):
        body: Dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": obj.name,
                "labels": {"env": "dev"},
            },
            "spec": {
                "ports": [
                    {
                        "name": p.name,
                        "port": p.port,
                        "targetPort": p.target_port,
                        "protocol": p.protocol,
                    }
                    for p in obj.ports
                ],
                "selector": get_dev_sandbox_labels(obj.app),
            },
        }

        if original_obj:
            body["metadata"]["resourceVersion"] = original_obj.metadata.resourceVersion

        return body


class DevSandboxServiceDeserializer(AppEntityDeserializer["DevSandboxService", "WlApp"]):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "DevSandboxService":
        ports = [
            ServicePortPair(
                name=p.name,
                port=p.port,
                target_port=p.targetPort,
            )
            for p in kube_data.spec.ports
        ]
        return self.entity_type(app=app, name=kube_data.metadata.name, ports=ports)
