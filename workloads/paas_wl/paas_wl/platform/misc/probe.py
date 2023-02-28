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
from typing import Type, Union

from blue_krill.monitoring.probe.mysql import MySQLProbe, transfer_django_db_settings
from blue_krill.monitoring.probe.redis import RedisProbe, RedisSentinelProbe
from django.conf import settings

from paas_wl.utils.redisdb import is_redis_sentinel_backend

STREAM_CHANNEL_REDIS_URL = settings.STREAM_CHANNEL_REDIS_URL


class DBProbe(MySQLProbe):
    name = "engine-db"
    config = transfer_django_db_settings(settings.DATABASES["default"])


class _StreamChannelRedisProbe(RedisProbe):
    name = 'stream-channel-redis'
    redis_url = STREAM_CHANNEL_REDIS_URL


class _StreamChannelRedisSentinelProbe(RedisSentinelProbe):
    name = 'stream-channel-redis'
    redis_url = STREAM_CHANNEL_REDIS_URL
    master_name = settings.SENTINEL_MASTER_NAME
    sentinel_kwargs = {'password': settings.SENTINEL_PASSWORD}


def _get_redis_probe_cls() -> Union[Type[_StreamChannelRedisSentinelProbe], Type[_StreamChannelRedisProbe]]:
    if is_redis_sentinel_backend(STREAM_CHANNEL_REDIS_URL):
        return _StreamChannelRedisSentinelProbe
    return _StreamChannelRedisProbe


StreamChannelRedisProbe = _get_redis_probe_cls()
