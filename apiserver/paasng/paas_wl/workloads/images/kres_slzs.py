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
from typing import TYPE_CHECKING, Dict, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer
from paas_wl.utils.text import b64decode, b64encode
from paas_wl.workloads.images import constants
from paas_wl.workloads.images.entities import ImageCredential
from paas_wl.workloads.images.utils import make_image_pull_secret_name

if TYPE_CHECKING:
    from paas_wl.workloads.images.kres_entities import ImageCredentials

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
            'data': {constants.KUBE_DATA_KEY: b64encode(json.dumps(obj.build_dockerconfig()))},
        }


class ImageCredentialsDeserializer(AppEntityDeserializer['ImageCredentials']):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance):
        if kube_data.type != constants.KUBE_SECRET_TYPE:
            raise ValueError(f"Invalid kube resource: {kube_data.type}")

        res_name = make_image_pull_secret_name(app)
        if kube_data.metadata.name != res_name:
            logger.warning(
                f"unexpected resource name, given is '{kube_data.metadata.name}', but expected is '{res_name}'"
            )

        b64encoded = kube_data.data[constants.KUBE_DATA_KEY]
        config: Dict[str, Dict] = json.loads(b64decode(b64encoded))["auths"]

        # Only deserialize the first auths info
        credentials = [
            ImageCredential(registry=registry, username=auth["username"], password=auth["password"])
            for registry, auth in config.items()
        ]

        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            credentials=credentials,
        )
