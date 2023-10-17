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
from dataclasses import dataclass
from typing import Dict, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.base.kres import KConfigMap
from paas_wl.infras.resources.kube_res.base import (
    AppEntity,
    AppEntityDeserializer,
    AppEntityManager,
    AppEntitySerializer,
)
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound

logger = logging.getLogger(__name__)


class ConfigMapSerializer(AppEntitySerializer['ConfigMap']):
    api_version = 'v1'

    def serialize(self, obj: 'ConfigMap', original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        return {
            'apiVersion': self.api_version,
            'kind': 'ConfigMap',
            'metadata': {
                'name': obj.name,
                'namespace': obj.app.namespace,
            },
            'data': obj.data,
        }


class ConfigMapDeserializer(AppEntityDeserializer['ConfigMap']):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> 'ConfigMap':
        return ConfigMap(
            app=app,
            name=kube_data.metadata.name,
            data=kube_data.data,
        )


@dataclass
class ConfigMap(AppEntity):
    data: str

    class Meta:
        kres_class = KConfigMap
        deserializer = ConfigMapDeserializer
        serializer = ConfigMapSerializer


class ConfigMapManager(AppEntityManager[ConfigMap]):
    def __init__(self):
        super().__init__(ConfigMap)

    def delete(self, res: ConfigMap, non_grace_period: bool = False):
        namespace = res.app.namespace
        config_name = res.name

        try:
            existed_one = self.get(app=res.app, name=config_name)
        except AppEntityNotFound:
            logger.info("BkLogConfig<%s/%s> does not exist, will skip delete", namespace, config_name)
            return
        return super().delete(existed_one, non_grace_period)


configmap_kmodel = ConfigMapManager()
