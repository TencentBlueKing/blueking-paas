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

"""Basic utils for scheduler"""

import logging
from collections import OrderedDict
from collections.abc import Callable
from typing import TYPE_CHECKING, Dict, List, Optional

from django.conf import settings

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.constants import ClusterAnnotationKey
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resources.base.base import EnhancedApiClient, get_client_by_cluster_name
from paas_wl.utils.basic import make_subdict

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models.config import Config


def _make_id(target):
    if hasattr(target, "__func__"):
        return (id(target.__self__), id(target.__func__))
    return id(target)


class LabelTolerationProviders:
    """Allow registering extra functions for labels/tolerations"""

    def __init__(self):
        self._registered_funcs_labels = OrderedDict()
        self._registered_funcs_tolerations = OrderedDict()

    def register_labels(self, func: Callable):
        # Use id to avoid duplicated registrations
        self._registered_funcs_labels[_make_id(func)] = func
        return func

    def register_tolerations(self, func: Callable):
        self._registered_funcs_tolerations[_make_id(func)] = func
        return func

    def get_labels(self, app: WlApp) -> Dict:
        """Gather all labels for given app."""
        result = {}
        for func in self._registered_funcs_labels.values():
            result.update(func(app))
        return result

    def get_tolerations(self, app: WlApp) -> Dict:
        """Gather all tolerations for given app."""
        result = {}
        for func in self._registered_funcs_tolerations.values():
            result.update(func(app))
        return result


label_toleration_providers = LabelTolerationProviders()


def get_full_node_selector(app: WlApp, config: Optional["Config"] = None) -> Dict:
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
    result.update(label_toleration_providers.get_labels(app))
    return result


def get_full_tolerations(app: WlApp, config: Optional["Config"] = None) -> List:
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


def get_slugbuilder_resources(app: WlApp) -> Dict[str, Dict[str, str]]:
    """获取 slugbuilder 资源配额（允许根据集群自定义）

    :return: {"requests": {"cpu": "1", "memory": "1Gi"}, "limits": {"cpu": "1", "memory": "1Gi"}}
    """
    annos = get_cluster_by_app(app).annotations
    if res := annos.get(ClusterAnnotationKey.SLUGBUILDER_RESOURCE_QUOTA):
        return res

    return settings.SLUGBUILDER_RESOURCES_SPEC


def get_client_by_app(app: WlApp) -> EnhancedApiClient:
    """Get kubernetes client by given app"""
    # TODO 增加一个带过期的缓存?
    # 可参考 https://stackoverflow.com/questions/31771286/python-in-memory-cache-with-time-to-live
    cluster = get_cluster_by_app(app)
    return get_client_by_cluster_name(cluster.name)


# ref: https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/
_VALID_TOLERATION_KEYS = {"key", "effect", "operator", "value", "tolerationSeconds"}


def standardize_tolerations(data) -> List:
    """standardize tolerations, will remove unrelated fields

    :return: List of toleration definitions
    """
    if isinstance(data, list):
        return [make_subdict(d, allowed_keys=_VALID_TOLERATION_KEYS) for d in data]
    else:
        logger.warning("Unknown tolerations format, data: %s", data)
        return []
