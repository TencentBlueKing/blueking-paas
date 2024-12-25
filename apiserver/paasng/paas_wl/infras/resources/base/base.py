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

"""Base utils for kubernetes scheduler"""

import logging
from functools import lru_cache
from typing import Dict, List

from blue_krill.connections.ha_endpoint_pool import HAEndpointPool
from django.utils import timezone
from kubernetes.client import ApiClient as BaseApiClient
from kubernetes.client.rest import RESTClientObject
from urllib3.exceptions import HTTPError

from paas_wl.infras.cluster.models import EnhancedConfiguration
from paas_wl.infras.cluster.pools import ContextConfigurationPoolMap
from paasng.core.core.storages.redisdb import get_default_redis

logger = logging.getLogger(__name__)


def get_global_configuration_pool() -> Dict[str, HAEndpointPool]:
    """Get the global config pool object from cache"""
    last_modified = _GlobalConfigLastModified().get()
    return _get_global_configuration_pool(last_modified)


@lru_cache
def _get_global_configuration_pool(last_modified: str) -> Dict[str, HAEndpointPool]:
    """Get the global config pool object.

    NOTE: This function is cached for performance. When the clusters have been updated,
    the cache must be cleared.

    :param last_modified: The global config last modified. 与 lru_cache 配合使用, 如果 last_modified 发生变化, 则缓存失效,
      从数据库重新加载
    """
    return ContextConfigurationPoolMap.from_db()


def invalidate_global_configuration_pool():
    """Invalidate the global config pool object cache"""
    _GlobalConfigLastModified().update()


class EnhancedApiClient(BaseApiClient):
    """Enhanced Kubernetes ApiClient, with some extra features:

    1. Client-side HA support using multiple endpoints
    2. Hostname overridden(via custom resolver).

    Arguments:

    :param ep_pool: Endpoints Pool object.
    """

    def __init__(self, ep_pool: HAEndpointPool, *args, **kwargs):
        self.ep_pool = ep_pool
        configuration = ep_pool.get()
        super().__init__(configuration, *args, **kwargs)

    def call_api(self, *args, **kwargs):
        """Call Kubernetes API"""
        self.ep_pool.elect()

        # WARNING: Although self.configuration was modified, some initial property such as `client_side_validation`
        # will stay intact because it's value was set in `BaseApiClient.__init__` method. This behaviour is not
        # harmful to current implementation, but due to this vulnerability, we may have to change current
        # implementation(e.g. create another `Client` object) in order to make things work in the future.
        self.configuration: EnhancedConfiguration = self.ep_pool.get()
        try:
            with self.configuration.activate_resolver():
                logger.debug("Send request to Kubernetes API %s...", self.configuration.host)
                ret = super().call_api(*args, **kwargs)
        except HTTPError:
            self.ep_pool.fail()
            raise
        else:
            self.ep_pool.succeed()
        return ret

    @property
    def rest_client(self) -> RESTClientObject:
        return make_rest_client(self.configuration)

    @rest_client.setter
    def rest_client(self, client: RESTClientObject):
        """Ignore any set operations on `rest_client` attribute, the object will be built and
        returned by the property object anyway.
        """


@lru_cache(maxsize=128)
def make_rest_client(configuration: EnhancedConfiguration) -> RESTClientObject:
    """Use LRU cache to avoid re-creating HTTP connections"""
    return RESTClientObject(configuration)


def get_all_cluster_names() -> List[str]:
    return list(get_global_configuration_pool().keys())


def get_client_by_cluster_name(cluster_name: str) -> EnhancedApiClient:
    """Initialize an kubernetes api client object by given context

    TODO/IMPORTANT: Add cache to reuse connection pools which were maintained by every individual client object
    """
    if not cluster_name:
        raise ValueError("context_name must not be empty")

    if cluster_name not in get_all_cluster_names():
        # if the context which user want to use do not exist, raise a ValueError
        raise ValueError(f'context "{cluster_name}" not found in settings, ' f"all context: {get_all_cluster_names()}")

    ep_pool = get_global_configuration_pool()[cluster_name]
    return EnhancedApiClient(ep_pool=ep_pool)


class _GlobalConfigLastModified:
    """Global config last modified. This is just used to identify the global config has been updated or not"""

    _key = "config_last_modified"

    def __init__(self):
        self.redis = get_default_redis()

    def get(self) -> str:
        """get current last modified"""
        if v := self.redis.get(self._key):
            return v.decode()

        v = self._get_time_now()
        self.redis.set(self._key, v)
        return v

    def update(self):
        """update last modified to indicate global config has been updated"""
        self.redis.set(self._key, self._get_time_now())

    @staticmethod
    def _get_time_now() -> str:
        return timezone.now().strftime("%Y%m%d%H%M%S")
