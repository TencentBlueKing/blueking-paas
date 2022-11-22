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
import redis
from blue_krill.redis_tools.sentinel import SentinelBackend
from django.conf import settings

from paas_wl.settings.utils import is_redis_sentinel_backend

_stream_channel_redisdb = None


def get_stream_channel_redis() -> redis.Redis:
    """Get redis for streaming communication with pass-ng"""
    global _stream_channel_redisdb
    if _stream_channel_redisdb is not None:
        return _stream_channel_redisdb

    _stream_channel_redisdb = _get_redis_from_url(settings.STREAM_CHANNEL_REDIS_URL)
    return _stream_channel_redisdb


_default_redisdb = None


def get_default_redis() -> redis.Redis:
    """Get default redis instance"""
    global _default_redisdb
    if _default_redisdb is not None:
        return _default_redisdb

    _default_redisdb = _get_redis_from_url(settings.REDIS_URL)
    return _default_redisdb


def _get_redis_from_url(url: str) -> redis.Redis:
    # Get connection options from settings
    connection_options = settings.REDIS_CONNECTION_OPTIONS

    if is_redis_sentinel_backend(url):
        backend = SentinelBackend(
            url, settings.SENTINEL_MASTER_NAME, {'password': settings.SENTINEL_PASSWORD}, **connection_options
        )
        return backend.client

    return redis.from_url(url, **connection_options)
