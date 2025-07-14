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
from paas_wl.bk_app.dev_sandbox.labels import get_dev_sandbox_labels
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandboxConfigMap


class DevSandboxConfigMapSerializer(AppEntitySerializer["DevSandboxConfigMap"]):
    """ConfigMap 序列化器"""

    def serialize(self, obj: "DevSandboxConfigMap", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        body: Dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": obj.name,
                "labels": get_dev_sandbox_labels(obj.app),
            },
            "data": obj.data,
        }

        if original_obj:
            body["metadata"]["resourceVersion"] = original_obj.metadata.resourceVersion

        return body


class DevSandboxConfigMapDeserializer(AppEntityDeserializer["DevSandboxConfigMap"]):
    """ConfigMap 反序列化器"""

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "DevSandboxConfigMap":
        data = kube_data.data if hasattr(kube_data, "data") else {}

        return self.entity_type(app=app, name=kube_data.metadata.name, data=data)
