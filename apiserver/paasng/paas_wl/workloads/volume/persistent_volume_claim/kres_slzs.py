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

from typing import TYPE_CHECKING, Dict, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer

if TYPE_CHECKING:
    from paas_wl.workloads.volume.persistent_volume_claim.kres_entities import PersistentVolumeClaim


class PersistentVolumeClaimSerializer(AppEntitySerializer["PersistentVolumeClaim"]):
    api_version = "v1"

    def serialize(
        self, obj: "PersistentVolumeClaim", original_obj: Optional[ResourceInstance] = None, **kwargs
    ) -> Dict:
        return {
            "apiVersion": self.api_version,
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": obj.name,
                "namespace": obj.app.namespace,
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {"requests": {"storage": obj.storage}},
                "storageClassName": obj.storage_class_name,
                "volumeMode": "Filesystem",
            },
        }


class PersistentVolumeClaimDeserializer(AppEntityDeserializer["PersistentVolumeClaim", "WlApp"]):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "PersistentVolumeClaim":
        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            storage=kube_data.spec.resources.requests.storage,
            storage_class_name=kube_data.spec.storageClassName,
        )
