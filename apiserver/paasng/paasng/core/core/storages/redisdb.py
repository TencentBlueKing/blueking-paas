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

import pickle

import redis
from blue_krill.redis_tools.sentinel import SentinelBackend
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from paasng.settings.utils import is_redis_sentinel_backend

_default_redisdb = None


def get_default_redis(settings_prefix: str = "REDIS_") -> redis.Redis:
    """Get the default redis database as connection pool instance

    :param settings_prefix: The prefix string for redis related settings
    """
    global _default_redisdb
    if _default_redisdb is not None:
        return _default_redisdb

    try:
        server_url = getattr(settings, f"{settings_prefix}URL")
    except AttributeError:
        raise ImproperlyConfigured(f"Please set {settings_prefix}URL in settings in order to use redis!")

    # Get connection options from settings
    connection_options = getattr(settings, f"{settings_prefix}CONNECTION_OPTIONS", {})

    if is_redis_sentinel_backend(server_url):
        backend = SentinelBackend(
            server_url, settings.SENTINEL_MASTER_NAME, {"password": settings.SENTINEL_PASSWORD}, **connection_options
        )
        _default_redisdb = backend.client
    else:
        _default_redisdb = redis.from_url(server_url, **connection_options)

    return _default_redisdb


class DefaultRediStore:
    """Store snapshot data, use redis as backend."""

    def __init__(self, rkey: str, expires_in: int = 3600 * 24):
        self.redis_db = get_default_redis()
        self.rkey = rkey
        self.expires_in = expires_in

    def save(self, data):
        self.redis_db.setex(self.rkey, value=pickle.dumps(data), time=self.expires_in)

    def get(self):
        val = self.redis_db.get(self.rkey)
        if val is None:
            return None
        return pickle.loads(val)
