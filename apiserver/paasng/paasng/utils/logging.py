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

import logging

import redis
from logstash import formatter

from .local import local

# logging 模块只往标准输出打日志, 避免出现对 redis 的循环依赖
logger = logging.getLogger("console")


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
            assert self.formatter
            self.client.rpush(self.queue_name, self.formatter.format(record))
        except Exception:
            logger.exception('LogstashRedisHandler push to redis error')


class RequestIDFilter(logging.Filter):
    """RequestID 过滤器. 将 local.request_id 写入 LogRecord, 用于在日志中标识追踪同一请求链路"""

    def filter(self, record):
        record.request_id = local.request_id
        return True
