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
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.platform.applications.models import App
from paas_wl.resources.base import kres
from paas_wl.resources.kube_res.base import AppEntity, AppEntityDeserializer, AppEntityManager, AppEntitySerializer
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.text import b64decode, b64encode
from paas_wl.workloads.images import constants
from paas_wl.workloads.images.models import AppImageCredential

logger = logging.getLogger(__name__)


class ImageCredentialsSerializer(AppEntitySerializer['ImageCredentials']):
    api_version = "v1"

    def serialize(self, obj: 'ImageCredentials', original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        return {
            'apiVersion': self.api_version,
            'kind': 'Secret',
            'type': constants.KUBE_SECRET_TYPE,
            'metadata': {
                'name': obj.name,
                'namespace': obj.app.namespace,
            },
            'data': {constants.KUBE_DATA_KEY: b64encode(json.dumps(self._build_dockerconfig(obj)))},
        }

    def _build_dockerconfig(self, obj: 'ImageCredentials') -> Dict:
        return {
            "auths": {
                item.registry: {
                    "username": item.username,
                    "password": item.password,
                    "auth": b64encode(f"{item.username}:{item.password}"),
                }
                for item in obj.credentials
            }
        }


class ImageCredentialsDeserializer(AppEntityDeserializer['ImageCredentials']):
    def deserialize(self, app: App, kube_data: ResourceInstance):
        if kube_data.type != constants.KUBE_SECRET_TYPE:
            raise ValueError(f"Invalid kube resource: {kube_data.type}")

        if kube_data.metadata.name != constants.KUBE_RESOURCE_NAME:
            logger.warning(
                "unexpected resource name, "
                f"given is '{kube_data.metadata.name}', but expected is '{constants.KUBE_RESOURCE_NAME}'"
            )

        b64encoded = kube_data.data[constants.KUBE_DATA_KEY]
        config: Dict[str, Dict] = json.loads(b64decode(b64encoded))["auths"]

        # Only deserialize the first auths info
        credentials = [
            ImageCredential(registry=registry, username=auth["username"], password=auth["password"])
            for registry, auth in config.items()
        ]

        return ImageCredentials(
            app=app,
            name=kube_data.metadata.name,
            credentials=credentials,
        )


@dataclass
class ImageCredential:
    registry: str
    username: str
    password: str


@dataclass
class ImageCredentials(AppEntity):
    credentials: List[ImageCredential]

    class Meta:
        kres_class = kres.KSecret
        deserializer = ImageCredentialsDeserializer
        serializer = ImageCredentialsSerializer

    @classmethod
    def load_from_app(cls, app: App) -> 'ImageCredentials':
        qs = AppImageCredential.objects.filter(app=app)
        credentials = [
            ImageCredential(registry=instance.registry, username=instance.username, password=instance.password)
            for instance in qs
        ]
        return ImageCredentials(
            app=app,
            name=constants.KUBE_RESOURCE_NAME,
            credentials=credentials,
        )


class ImageCredentialsManager(AppEntityManager[ImageCredentials]):
    def __init__(self):
        super().__init__(ImageCredentials)

    def delete(self, res: ImageCredentials, non_grace_period: bool = False):
        namespace = res.app.namespace
        secret_name = res.name

        try:
            existed = self.get(app=res.app, name=secret_name)
        except AppEntityNotFound:
            logger.info("Secret<%s/%s> does not exist, will skip delete", namespace, secret_name)
            return
        return super().delete(existed, non_grace_period)


credentials_kmodel = ImageCredentialsManager()
