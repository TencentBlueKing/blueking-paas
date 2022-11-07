# -*- coding: utf-8 -*-

import logging

import redis
from logstash import formatter

from .local import local


class LogstashRedisHandler(logging.Handler):
    def __init__(self, redis_url, queue_name='', message_type='logstash', tags=None):
        """
        初始化，延迟时间默认1秒钟
        """
        logging.Handler.__init__(self)
        self.queue_name = queue_name
        pool = redis.BlockingConnectionPool.from_url(redis_url, max_connections=600, timeout=1)
        self.client = redis.Redis(connection_pool=pool)
        self.formatter = formatter.LogstashFormatterVersion1(message_type, tags, fqdn=False)

    def emit(self, record):
        """
        提交数据
        """
        try:
            assert self.formatter is not None
            self.client.rpush(self.queue_name, self.formatter.format(record))
        except Exception:
            logger.exception('LogstashRedisHandler push to redis error')


class RequestIDFilter(logging.Filter):
    """RequestID 过滤器. 将 local.request_id 写入 LogRecord, 用于在日志中标识追踪同一请求链路"""

    def filter(self, record):
        record.request_id = local.request_id
        return True


logger = logging.getLogger('root')
