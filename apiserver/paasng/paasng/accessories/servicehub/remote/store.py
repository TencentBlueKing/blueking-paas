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

"""Storage for remote services"""

import copy
import json
import logging
import pickle
from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Set

from django.conf import settings
from django.utils.encoding import force_bytes, force_str

from paasng.core.core.storages.redisdb import get_default_redis

from .client import RemoteSvcConfig
from .exceptions import ServiceConfigNotFound, ServiceNotFound

logger = logging.getLogger(__name__)

_g_services_store = None


def _dumps(internal_value: Dict) -> str:
    """dumps a **internal** object to redis savable str"""
    return force_str(pickle.dumps(internal_value), encoding="latin-1")


def _loads(dumped: bytes) -> Dict:
    """load a dumped str to **internal** object"""
    try:
        # NOTE: 以前的数据是直接使用 json.dumps 存储的, 为了兼容旧数据, 先尝试使用 json.loads 读取数据
        return json.loads(dumped)
    except json.decoder.JSONDecodeError:
        return pickle.loads(force_bytes(dumped, encoding="latin-1"))


def get_remote_store():
    """Get the single instanced remote services database object"""
    global _g_services_store
    if _g_services_store is None:
        _g_services_store = RemoteServiceStore()
    return _g_services_store


class StoreMixin:
    get: Callable
    all: Callable

    def filter(self, region: str, conditions: Optional[Dict] = None) -> List[Dict]:
        """Find a list of services by given conditions

        :param conditions: a dict of conditions, eg. {"category": 1}
        """
        result = []
        conditions = conditions or {}
        for service in self.all():
            if not self._svc_supports_region(service, region):
                continue

            for key, value in conditions.items():
                if service.get(key) != value:
                    break
            else:
                # Append the item to result when the forloop ends without break
                result.append(copy.deepcopy(service))
        return result

    def bulk_get(self, uuids: List[str]) -> List[Dict]:
        """Get multiple service instances by a list of uuids

        :returns: a list of service object, if a service can not be found by given uuid, use
            None instead.
        """
        items = []
        for uuid in uuids:
            try:
                items.append(self.get(uuid))
            except ServiceNotFound:
                logger.warning(f"bulk_get: can not find a service by uuid {uuid}")
                items.append(None)
        return items

    @staticmethod
    def _svc_supports_region(svc_data: Dict, region: str) -> bool:
        """Check if a service supports given region"""
        return any(plan["properties"].get("region") == region for plan in svc_data["plans"])


class MemoryStore(StoreMixin):
    """Remote service store"""

    def __init__(self):
        self._map_id_to_service = OrderedDict()
        self._map_id_to_config = {}

    def bulk_upsert(self, services: List[Dict], meta_info: Optional[Dict], source_config: RemoteSvcConfig):
        """Insert the service if identical uuid does not exists, otherwise update it.

        :raises ValueError: When services with the same uuid and different names in the service configuration.
        """
        for service in services:
            service["_meta_info"] = meta_info

            legacy_svc = self._map_id_to_service.get(service["uuid"])
            if legacy_svc:
                legacy_config = self._map_id_to_config[service["uuid"]]
                if legacy_config["name"] != source_config.name:
                    raise ValueError(f'Service uuid={service["uuid"]} with a different source name already exists')

            self._map_id_to_service[service["uuid"]] = service
            self._map_id_to_config[service["uuid"]] = source_config

    def get_source_config(self, uuid: str) -> RemoteSvcConfig:
        """Get the source remote svc config by service uuid"""
        return self._map_id_to_config[uuid]

    def get(self, uuid: str) -> Dict:
        """Get a service instance by uuid"""
        try:
            return copy.deepcopy(self._map_id_to_service[uuid])
        except KeyError:
            raise ServiceNotFound(f"remote service with id={uuid} not found")

    def all(self) -> List[Dict]:
        """List all services"""
        return copy.deepcopy(list(self._map_id_to_service.values()))

    def empty(self):
        """Empty this store"""
        self._map_id_to_service = OrderedDict()
        self._map_id_to_config = {}


class RedisStore(StoreMixin):
    cache_key = "REDIS_"

    # Namespace for redis keys, when there are multiple running paas instances. If you modified the core logic of Store
    # class, it's required to update namespace to avoid data conflicts.
    namespace = "1"
    encoding = "utf-8"
    registered_services_key = namespace + "remote:registered:service:uuid"
    expires = settings.REMOTE_SERVICES_UPDATE_INTERVAL_MINUTES * 60 * 10

    def __init__(self):
        self.redis = get_default_redis(self.cache_key)

    def _make_svc_info_key(self, uuid: str) -> str:
        return self.namespace + f"remote:service:info:{uuid}"

    def _make_svc_config_key(self, uuid: str) -> str:
        return self.namespace + f"remote:service:config:{uuid}"

    def get_service_keys(self) -> Set[str]:
        """Get all registered service key"""
        result = self.redis.smembers(self.registered_services_key)
        return {force_str(i, encoding=self.encoding) for i in result}

    def bulk_upsert(self, services: List[Dict], meta_info: Optional[Dict], source_config: RemoteSvcConfig):
        """Insert the service if identical uuid does not exists, otherwise update it.

        :param meta_info: Service's meta info, including `version` etc.
        :raises ValueError: When services with the same uuid and different names in the service configuration.
        """
        redis_client = self.redis
        config = source_config.to_json()
        for service in services:
            service["_meta_info"] = meta_info

            sid = service["uuid"]
            info_key = self._make_svc_info_key(sid)
            config_key = self._make_svc_config_key(sid)

            legacy_config = redis_client.get(config_key)
            # 如果新的配置项中的服务名 与 缓存中服务名不一致，则不更新，服务的其他配置发生变更可更新
            if legacy_config and _loads(legacy_config)["name"] != config["name"]:
                raise ValueError(f'Service uuid={service["uuid"]} with a different source name already exists')

            pipe = redis_client.pipeline()
            pipe.set(info_key, _dumps(service), self.expires)
            pipe.set(config_key, _dumps(config), self.expires)
            pipe.sadd(self.registered_services_key, sid.encode(self.encoding))
            pipe.execute()

    def get_source_config(self, uuid: str) -> RemoteSvcConfig:
        """Get the source remote svc config by service uuid"""
        config = self.redis.get(self._make_svc_config_key(uuid))
        if config is None:
            raise ServiceConfigNotFound(f"Service config uuid={uuid} not found")
        return RemoteSvcConfig.from_json(_loads(config))

    def get(self, uuid: str) -> Dict:
        """Get a service instance by uuid"""
        result = self.redis.get(self._make_svc_info_key(uuid))
        if result is None:
            raise ServiceNotFound(f"remote service with id={uuid} not found")

        return _loads(result)

    def all(self) -> List[Dict]:
        """List all services"""
        keys = self.get_service_keys()
        if not keys:
            return []

        pipe = self.redis.pipeline()
        for k in keys:
            pipe.get(self._make_svc_info_key(k))

        results = []
        for i in pipe.execute():
            if i:
                results.append(_loads(i))

        return results

    def empty(self):
        """Empty this store"""
        keys = self.get_service_keys()
        if not keys:
            return

        pipe = self.redis.pipeline()
        for i in keys:
            pipe.delete(self._make_svc_config_key(i))
            pipe.delete(self._make_svc_info_key(i))

        pipe.delete(self.registered_services_key)
        pipe.execute()


RemoteServiceStore = RedisStore
