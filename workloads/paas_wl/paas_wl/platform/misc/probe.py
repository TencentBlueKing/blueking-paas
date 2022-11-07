# -*- coding: utf-8 -*-
from typing import Type, Union

from blue_krill.monitoring.probe.mysql import MySQLProbe, transfer_django_db_settings
from blue_krill.monitoring.probe.redis import RedisProbe, RedisSentinelProbe
from django.conf import settings

from paas_wl.settings.utils import is_redis_sentinel_backend

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
