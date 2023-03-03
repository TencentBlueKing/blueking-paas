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
"""Basic utils for scheduler
"""
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.egress.models import RCStateAppBinding
from paas_wl.platform.applications.models.app import EngineApp
from paas_wl.resources.base.base import EnhancedApiClient, get_client_by_cluster_name
from paas_wl.utils.basic import make_subdict

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paas_wl.platform.applications.models.config import Config


def get_full_node_selector(app: EngineApp, config: Optional['Config'] = None) -> Dict:
    """An app's node_selector was constituted by many parts.

    1. "node_selector" field in Config object
    2. when app was bound with ClusterState, use the state object's labels
    3. cluster's "default_node_selector", when configured

    Always use this function to get an app's FULL node_selector.
    """
    # Read cluster's "default_node_selector" as default result
    cluster = get_cluster_by_app(app)
    result = cluster.default_node_selector or {}

    # Merge with app's config
    config = config or app.config_set.latest()
    result.update(config.node_selector or {})

    # Inject ClusterState labels when bound
    try:
        binding = RCStateAppBinding.objects.get(app=app)
    except RCStateAppBinding.DoesNotExist:
        pass
    else:
        result.update(binding.state.to_labels())
    return result


def get_full_tolerations(app: EngineApp, config: Optional['Config'] = None) -> List:
    """An app's tolerations was constituted by many parts.

    1. "tolerations" field in Config object
    2. cluster's "default_tolerations", when configured

    Always use this function to get an app's FULL tolerations.
    """
    config = config or app.config_set.latest()
    results = config.tolerations or []

    # Merge from cluster's "default_tolerations"
    cluster = get_cluster_by_app(app)
    results.extend(cluster.default_tolerations or [])
    return standardize_tolerations(results)


def get_client_by_app(app: EngineApp) -> EnhancedApiClient:
    """Get kubernetes client by given app"""
    cluster = get_cluster_by_app(app)
    return get_client_by_cluster_name(cluster.name)


# ref: https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/
_VALID_TOLERATION_KEYS = {'key', 'effect', 'operator', 'value', 'tolerationSeconds'}


def standardize_tolerations(data) -> List:
    """standardize tolerations, will remove unrelated fields

    :return: List of toleration definitions
    """
    if isinstance(data, list):
        return [make_subdict(d, allowed_keys=_VALID_TOLERATION_KEYS) for d in data]
    else:
        logger.warning("Unknown tolerations format, data: %s", data)
        return []
