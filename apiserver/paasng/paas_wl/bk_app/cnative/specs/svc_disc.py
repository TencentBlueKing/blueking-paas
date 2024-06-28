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

import base64
import json
import logging
from typing import Any, Dict, List

from django.utils.encoding import force_bytes, force_str

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import KConfigMap
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.declarative.deployment.resources import BkSaaSItem
from paasng.platform.declarative.deployment.svc_disc import BkSaaSAddrDiscoverer

logger = logging.getLogger(__name__)


def apply_configmap(env: ModuleEnvironment, bk_app_res: BkAppResource):
    """Apply the ConfigMap resource that contains the service discovery data to the
    given environment, the ConfigMap might be deleted if the service discovery config
    is absent.
    :param env: The environment to apply the ConfigMap.
    :param bk_app_res: The BkAppResource object.
    """
    svc_disc = bk_app_res.spec.svcDiscovery
    mgr = ConfigMapManager(env, bk_app_name=bk_app_res.metadata.name)
    if not (svc_disc and svc_disc.bkSaaS):
        # TODO: Only remove the configmap if the app previously had a valid svc-discovery
        # config, don't perform the remove() operation every time.
        logger.debug("No service discovery config found, remove the ConfigMap if exists")
        mgr.remove()
        return

    # Transform the items to get addresses
    items = [BkSaaSItem(bk_app_code=obj.bkAppCode, module_name=obj.moduleName) for obj in svc_disc.bkSaaS]
    addrs = BkSaaSAddrDiscoverer().get(items)

    # Write the ConfigMap resource for current BkApp
    logger.info("Writing the service discovery addresses to ConfigMap, bk_app_name: %s", mgr.bk_app_name)
    mgr.write(addrs)


class ConfigMapManager:
    """The manager for service discovery ConfigMap.

    :param env: The environment.
    :param bk_app_name: The name of BkApp resource.
    """

    key_bk_saas = "bk_saas_encoded_json"

    def __init__(self, env: ModuleEnvironment, bk_app_name: str):
        self.env = env
        self.wl_app = WlApp.objects.get(pk=env.engine_app_id)
        self.bk_app_name = bk_app_name

    def read_data(self) -> Dict:
        """Read the data of the ConfigMap resource.

        :raise ResourceMissing: If the ConfigMap resource doesn't exist.
        """
        with get_client_by_app(self.wl_app) as client:
            res = KConfigMap(client).get(self.resource_name, namespace=self.wl_app.namespace)
            return res.data

    def write(self, saas_addrs: List[Dict]):
        """Write the addresses to the ConfigMap.

        :param saas_addrs: The addresses of bk-SaaS to write, see `BkSaaSAddrDiscoverer` to check the format.
        """
        with get_client_by_app(self.wl_app) as client:
            body = {
                "metadata": {"name": self.resource_name},
                "data": {self.key_bk_saas: self.encode_data(saas_addrs)},
            }
            KConfigMap(client).create_or_update(
                self.resource_name,
                namespace=self.wl_app.namespace,
                body=body,
                update_method="patch",
            )

    def remove(self):
        """Remove the ConfigMap resource."""
        with get_client_by_app(self.wl_app) as client:
            KConfigMap(client).delete(self.resource_name, namespace=self.wl_app.namespace)

    def exists(self) -> bool:
        """Check if the ConfigMap resource exists.

        :return: Whether the ConfigMap exists.
        """
        with get_client_by_app(self.wl_app) as client:
            try:
                # TODO: Write another faster method which don't read the whole object in KRes
                KConfigMap(client).get(self.resource_name, namespace=self.wl_app.namespace)
            except ResourceMissing:
                return False
            else:
                return True

    @property
    def resource_name(self) -> str:
        """Get the name of the ConfigMap object"""
        return f"svc-disc-results-{self.bk_app_name}"

    @staticmethod
    def encode_data(data: Any) -> str:
        """Encode data to string"""
        data_bytes = force_bytes(json.dumps(data))
        return force_str(base64.b64encode(data_bytes))

    @staticmethod
    def decode_data(data: str) -> Any:
        """Decode string data to object"""
        return json.loads(base64.b64decode(force_bytes(data)))
