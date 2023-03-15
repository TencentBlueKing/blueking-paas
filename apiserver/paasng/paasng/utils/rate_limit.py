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
import time

import redis
import wrapt
from blue_krill.data_types.enum import StructuredEnum
from rest_framework.response import Response
from rest_framework.status import HTTP_429_TOO_MANY_REQUESTS

from paasng.platform.core.storages.redisdb import get_default_redis

# 默认时间窗口长度：60s
DEFAULT_WINDOW_SIZE = 60
# 时间窗口内默认次数阈值
DEFAULT_THRESHOLD = 15


class UserAction(str, StructuredEnum):
    """用于频率限制的用户操作"""

    FETCH_DEPLOY_LOG = 'fetch_deploy_log'
    WATCH_PROCESSES = 'watch_processes'


class RedisTokenBucketRateLimiter:
    """基于 Redis 的令牌桶速率控制器"""

    def __init__(
        self,
        redis_db: redis.Redis,
        username: str,
        action: UserAction,
        window_size: int = DEFAULT_WINDOW_SIZE,
        threshold: int = DEFAULT_THRESHOLD,
    ):
        """
        :param redis_db: redis client
        :param username: 用户 ID
        :param action: 用户操作名
        :param window_size: 窗口时长（单位：秒，默认 60s）
        :param threshold: 时间窗口内的次数阈值
        """
        self.redis_db = redis_db
        self.username = username
        self.action = action
        self.window_size = window_size
        self.threshold = threshold
        self.key = self._gen_key()

    def is_allowed(self) -> bool:
        """
        是否允许当前行为（未受速率限制影响）

        令牌桶实现：
        +------------------------------------------+
        |               user request               |
        +------------------------------------------+
                           |
                           |
                           v
        +------------------------------------------+    < threshold     +------------------------------+
        |           check queue length             | -----------------> | [✓] lpush current timestamp  |
        +------------------------------------------+                    +------------------------------+
                           |
                           | >= threshold
                           v
        +------------------------------------------+   < window_size    +----------------------+
        |   check timedelta (current and oldest)   | -----------------> | [✗] cause rate limit |
        +------------------------------------------+                    +----------------------+
                           |
                           | >= window_size
                           v
        +------------------------------------------+
        |   [✓] rpop and lpush current timestamp   |
        +------------------------------------------+
        """
        cur_timestamp = int(time.time())

        if self.redis_db.llen(self.key) < self.threshold:
            self.redis_db.lpush(self.key, cur_timestamp)
            return True

        oldest_timestamp = int(self.redis_db.lindex(self.key, -1))  # type: ignore
        if cur_timestamp - oldest_timestamp >= self.window_size:
            self.redis_db.rpop(self.key)
            self.redis_db.lpush(self.key, cur_timestamp)
            return True

        return False

    def _gen_key(self) -> str:
        """生成 redis 中的 key"""
        return f'bk_paas3:token_bucket_rate_limit:{self.username}:{self.action}'


def rate_limits_on_view_func(
    action: UserAction,
    window_size: int = DEFAULT_WINDOW_SIZE,
    threshold: int = DEFAULT_THRESHOLD,
):
    """适用于 Django View 方法的装饰器，提供频率限制的能力"""

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        rate_limiter = RedisTokenBucketRateLimiter(
            get_default_redis(), instance.request.user.username, action, window_size, threshold
        )
        if not rate_limiter.is_allowed():
            return Response(status=HTTP_429_TOO_MANY_REQUESTS)

        return wrapped(*args, **kwargs)

    return wrapper
