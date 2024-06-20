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
from typing import TYPE_CHECKING, Dict, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer

from .entities import InvolvedObject, Source

if TYPE_CHECKING:
    from paas_wl.workloads.event.kres_entities import Event


class EventDeserializer(AppEntityDeserializer["Event"]):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "Event":
        involved_object = kube_data.involvedObject
        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            type=kube_data.type,
            message=kube_data.message,
            reason=kube_data.reason,
            # k8s 产生事件时，不写入 count 字段是否代表事件发生一次，待验证
            count=kube_data.get("count", 1),
            first_timestamp=kube_data.firstTimestamp,
            last_timestamp=kube_data.lastTimestamp,
            involved_object=InvolvedObject(
                kind=involved_object.kind,
                name=involved_object.name,
                namespace=getattr(involved_object, "namespace", None),
                api_version=involved_object.apiVersion,
            ),
            source=Source(
                component=kube_data.source.component,
                host=getattr(kube_data.source, "host", None),
            ),
        )


class EventSerializer(AppEntitySerializer["Event"]):
    api_version = "v1"

    def serialize(self, obj: "Event", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        return {
            "apiVersion": self.api_version,
            "kind": "Event",
            "metadata": {
                "name": obj.name,
                "namespace": obj.app.namespace,
            },
            "involvedObject": {
                "kind": obj.involved_object.kind,
                "name": obj.involved_object.name,
                "namespace": obj.involved_object.namespace,
                "apiVersion": obj.involved_object.api_version,
            },
            "source": {
                "component": obj.source.component,
                "host": obj.source.host,
            },
            "type": obj.type,
            "message": obj.message,
            "reason": obj.reason,
            "count": obj.count,
            "firstTimestamp": obj.first_timestamp,
            "lastTimestamp": obj.last_timestamp,
        }
