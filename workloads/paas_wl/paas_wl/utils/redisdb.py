# -*- coding: utf-8 -*-
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
