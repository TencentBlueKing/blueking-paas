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

"""Service discovery module"""
import base64
import json
import logging
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cattr
from django.conf import settings
from django.utils.encoding import force_bytes, force_str

from paasng.engine.constants import AppEnvName
from paasng.engine.controller.models import Cluster
from paasng.engine.deploy.env_vars import env_vars_providers
from paasng.engine.models import Deployment
from paasng.extensions.declarative.deployment.resources import BkSaaSItem
from paasng.extensions.declarative.models import DeploymentDescription
from paasng.platform.applications.models import Application
from paasng.platform.modules.helpers import get_module_clusters
from paasng.platform.modules.models import Module
from paasng.publish.entrance.exposer import get_preallocated_address

logger = logging.getLogger(__name__)


@env_vars_providers.register_deploy
def get_services_as_env_variables(deployment: Deployment) -> Dict[str, str]:
    """Get env vars which were defined by deployment description file"""
    try:
        deploy_desc = DeploymentDescription.objects.get(deployment=deployment)
    except DeploymentDescription.DoesNotExist:
        return {}

    svc_discovery = deploy_desc.get_svc_discovery()
    return BkSaaSEnvVariableFactory(svc_discovery.bk_saas).make()


class BkSaaSEnvVariableFactory:
    """Generate env variable from config"""

    variable_name = settings.CONFIGVAR_SYSTEM_PREFIX + "SERVICE_ADDRESSES_BKSAAS"

    def __init__(self, saas_items: List[BkSaaSItem]):
        self.saas_items = saas_items

    def make(self) -> Dict[str, str]:
        """Make env variables

        :returns: {KEY: <base64 encoded services address>}
        """
        if not self.saas_items:
            return {}

        data = self._get_preallocated_addresses()
        return {self.variable_name: self.encode_data(data)}

    def _get_preallocated_addresses(self) -> List[Dict]:
        """Get each app_code's preallocated addresses"""
        data: List[Dict] = []
        for saas_item, clusters in self.extend_with_clusters(self.saas_items):
            value: Optional[Dict]
            try:
                value = get_preallocated_address(
                    saas_item.bk_app_code, module_name=saas_item.module_name, clusters=clusters
                )._asdict()
            except ValueError:
                value = None
            data.append({'key': cattr.unstructure(saas_item), 'value': value})
        return data

    @staticmethod
    def extend_with_clusters(
        items: Sequence[BkSaaSItem],
    ) -> Iterable[Tuple[BkSaaSItem, Optional[Dict[AppEnvName, Cluster]]]]:
        """Extends given `BkSaaSItem` objects with their clusters, if the SaaS has
        not been deployed yet, the cluster value will be `None`, otherwise the
        real cluster object will be returned.

        :param items: SaaS items.
        :returns: The original SaaS item and the cluster object iteratively.
        """
        for item in items:
            module = query_module(item)
            if module:
                # Return the actual cluster object of current module
                yield item, get_module_clusters(module)
            else:
                logger.info('Module not found in system, no cluster for %s', item)
                yield item, None

    @staticmethod
    def encode_data(data) -> str:
        """Encode dict data to string"""
        data_bytes = force_bytes(json.dumps(data))
        return force_str(base64.b64encode(data_bytes))

    @staticmethod
    def decode_data(data):
        """Decode string data to object"""
        return json.loads(base64.b64decode(force_bytes(data)))


def query_module(item: BkSaaSItem) -> Optional[Module]:
    """Try to get the Module object in database by given `BkSaaSItem` info"""
    try:
        app = Application.objects.get(code=item.bk_app_code)
    except Application.DoesNotExist:
        return None
    try:
        if not item.module_name:
            return app.get_default_module()
        return app.modules.get(name=item.module_name)
    except Module.DoesNotExist:
        return None
