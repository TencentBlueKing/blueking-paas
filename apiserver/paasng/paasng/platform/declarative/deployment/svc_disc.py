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

"""Service discovery module"""

import base64
import json
import logging
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cattr
from django.conf import settings
from django.utils.encoding import force_bytes, force_str

from paas_wl.infras.cluster.models import Cluster
from paasng.accessories.publish.entrance.preallocated import get_exposed_url_type, get_preallocated_address
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.entities import SvcDiscEntryBkSaaS
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.helpers import get_module_clusters
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


class BkSaaSEnvVariableFactory:
    """Generate env variable from config"""

    variable_name = settings.CONFIGVAR_SYSTEM_PREFIX + "SERVICE_ADDRESSES_BKSAAS"

    def __init__(self, saas_items: List[SvcDiscEntryBkSaaS]):
        self.saas_items = saas_items

    def make(self) -> Dict[str, str]:
        """Make env variables

        :returns: {KEY: <base64 encoded services address>}
        """
        if not self.saas_items:
            return {}

        data = BkSaaSAddrDiscoverer().get(self.saas_items)
        return {self.variable_name: self.encode_data(data)}

    @staticmethod
    def encode_data(data) -> str:
        """Encode data to string"""
        data_bytes = force_bytes(json.dumps(data))
        return force_str(base64.b64encode(data_bytes))

    @staticmethod
    def decode_data(data):
        """Decode string data to object"""
        return json.loads(base64.b64decode(force_bytes(data)))


# TODO: Move this class to another module which is dedicated to "service-discovery"
class BkSaaSAddrDiscoverer:
    """Get the service addresses of the given SaaS items"""

    def get(self, items: List[SvcDiscEntryBkSaaS]) -> List[Dict]:
        """Get preallocated addresses by a list of `BkSaaSItem` objects

        :return: A list of addresses dict which includes both environments.
        """
        data: List[Dict] = []
        for saas_item, clusters in self.extend_with_clusters(items):
            value: Optional[Dict]

            # Try to retrieve the exposed URL type in order to get a more accurate result.
            preferred_url_type = get_exposed_url_type(saas_item.bk_app_code, saas_item.module_name)
            try:
                value = get_preallocated_address(
                    saas_item.bk_app_code,
                    module_name=saas_item.module_name,
                    clusters=clusters,
                    preferred_url_type=preferred_url_type,
                )._asdict()
            except ValueError:
                value = None
            data.append({"key": cattr.unstructure(saas_item), "value": value})
        return data

    @staticmethod
    def extend_with_clusters(
        items: Sequence[SvcDiscEntryBkSaaS],
    ) -> Iterable[Tuple[SvcDiscEntryBkSaaS, Optional[Dict[AppEnvName, Cluster]]]]:
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
                logger.info("Module not found in system, no cluster for %s", item)
                yield item, None


def query_module(item: SvcDiscEntryBkSaaS) -> Optional[Module]:
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
